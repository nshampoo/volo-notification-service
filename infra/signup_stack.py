import json
from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_sns as sns
from aws_cdk import aws_ssm as ssm
from constructs import Construct

ROOT = Path(__file__).parent.parent
SPORTS = json.loads((ROOT / "config" / "sports.json").read_text())

# Created by hand with `aws ssm put-parameter --type SecureString`, because
# CloudFormation cannot create SecureString parameters. See README.
INVITE_CODE_PARAM = "/volo-notifier/invite-code"


class SignupStack(Stack):
    """Sign-up page (S3 + CloudFront) and the public subscribe Lambda."""

    def __init__(self, scope: Construct, construct_id: str, *, dropins_topic: sns.ITopic, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Private bucket. Only CloudFront can read it, through Origin Access Control.
        bucket = s3.Bucket(
            self,
            "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        distribution = cloudfront.Distribution(
            self,
            "Site",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            default_root_object="index.html",
            # North America and Europe edge locations only: the cheapest tier.
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )
        site_origin = f"https://{distribution.distribution_domain_name}"

        invite_code = ssm.StringParameter.from_secure_string_parameter_attributes(
            self, "InviteCode", parameter_name=INVITE_CODE_PARAM
        )

        subscribe_fn = lambda_.Function(
            self,
            "Subscribe",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            code=lambda_.Code.from_asset(str(ROOT / "services" / "subscribe"), exclude=["__pycache__"]),
            handler="subscribe.handler",
            timeout=Duration.seconds(10),
            memory_size=256,
            environment={
                "TOPIC_ARN": dropins_topic.topic_arn,
                "INVITE_CODE_PARAM": INVITE_CODE_PARAM,
                "ALLOWED_SPORTS": ",".join(s["slug"] for s in SPORTS),
            },
            log_group=logs.LogGroup(
                self,
                "SubscribeLogs",
                retention=logs.RetentionDays.ONE_MONTH,
                removal_policy=RemovalPolicy.DESTROY,
            ),
        )
        invite_code.grant_read(subscribe_fn)
        subscribe_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sns:Subscribe", "sns:ListSubscriptionsByTopic"],
                resources=[dropins_topic.topic_arn],
            )
        )
        subscribe_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["sns:SetSubscriptionAttributes"],
                # Subscription ARNs are the topic ARN plus ":<id>".
                resources=[f"{dropins_topic.topic_arn}:*"],
            )
        )

        # Public HTTPS endpoint. CORS only lets browsers call it from our page;
        # the invite code is what stops everyone else.
        subscribe_url = subscribe_fn.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE,
            cors=lambda_.FunctionUrlCorsOptions(
                allowed_origins=[site_origin],
                allowed_methods=[lambda_.HttpMethod.POST],
                allowed_headers=["content-type"],
            ),
        )

        # Upload web/ plus a generated config.json, then clear CloudFront's cache.
        s3deploy.BucketDeployment(
            self,
            "DeploySite",
            destination_bucket=bucket,
            sources=[
                s3deploy.Source.asset(str(ROOT / "web")),
                s3deploy.Source.json_data("config.json", {"subscribeUrl": subscribe_url.url, "sports": SPORTS}),
            ],
            distribution=distribution,
            distribution_paths=["/*"],
        )

        CfnOutput(self, "SiteUrl", value=site_origin)
        CfnOutput(self, "SubscribeUrl", value=subscribe_url.url)
