from invoke import task


@task(aliases=['ul'])
def update_license(ctx, license='/secrets/es5-license.json'):
    for elasticsearch_host in ('elasticsearch', 'elasticsearch2'):
        ctx.run(
            "curl -XPUT 'http://{0}:9200/_xpack/license?acknowledge=true' -H 'Content-Type: application/json' -d @{1}".format(
                elasticsearch_host, license))
