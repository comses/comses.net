from invoke import task


@task(aliases=["r"])
def run(ctx, target="html"):
    with ctx.cd("/docs"):
        ctx.run("make {}".format(target))
