from django.conf import settings
from invoke import task


@task(aliases=["ul"])
def update_license(ctx, license_path=None):
    es_hosts = ["elasticsearch"]
    if settings.DEPLOY_ENVIRONMENT.is_production:
        es_hosts.append("elasticsearch2")

    for elasticsearch_host in es_hosts:
        if license_path is None:
            ctx.run(
                "curl -XPOST 'http://{0}:9200/_xpack/license/start_basic?acknowledge=true'".format(
                    elasticsearch_host
                )
            )
        else:
            ctx.run(
                "curl -XPUT 'http://{0}:9200/_xpack/license?acknowledge=true' -H 'Content-Type: application/json' -d @{1}".format(
                    elasticsearch_host, license
                )
            )
