from invoke import task


@task(aliases=['r'])
def run(ctx, target='html'):
    with ctx.cd('/docs'):
        ctx.run('make {}'.format(target))
        if target == 'html':
            # without this css on gh-pages will not work
            ctx.run('touch build/html/.nojekyll')
