import aws_cdk as cdk
from aws_cdk import aws_sns as sns
from aws_cdk.assertions import Match, Template

from infra.signup_stack import SignupStack


def synth() -> Template:
    app = cdk.App()
    env = cdk.Environment(account="123456789012", region="us-east-1")
    topic_stack = cdk.Stack(app, "Topics", env=env)
    topic = sns.Topic(topic_stack, "Dropins")
    return Template.from_stack(SignupStack(app, "TestSignup", env=env, dropins_topic=topic))


def test_bucket_is_private():
    synth().has_resource_properties(
        "AWS::S3::Bucket",
        {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            }
        },
    )


def test_cloudfront_uses_origin_access_control_and_https():
    template = synth()
    template.resource_count_is("AWS::CloudFront::OriginAccessControl", 1)
    template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "DefaultRootObject": "index.html",
                    "DefaultCacheBehavior": Match.object_like({"ViewerProtocolPolicy": "redirect-to-https"}),
                }
            )
        },
    )


def test_subscribe_url_is_public_but_cors_locked_to_post():
    synth().has_resource_properties(
        "AWS::Lambda::Url",
        {"AuthType": "NONE", "Cors": Match.object_like({"AllowMethods": ["POST"]})},
    )


def test_subscribe_lambda_knows_allowed_sports():
    synth().has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "subscribe.handler",
            "Environment": {
                "Variables": Match.object_like({"ALLOWED_SPORTS": Match.string_like_regexp("^flag-football,")})
            },
        },
    )
