"""Tasks that are not namespaced go here"""

from invoke import task, call
from django.conf import settings
from core.utils import confirm
from .utils import dj, env


@task(aliases=["ss"])
def setup_site(ctx, site_name="CoRe @ CoMSES Net", site_domain="www.comses.net"):
    confirm(
        "This is a destructive process and will remove all existing root pages. Are you sure you want to run this? (y/n) "
    )
    dj(ctx, f'setup_site --site-name="{site_name}" --site-domain="{site_domain}"')
    if not settings.DEPLOY_ENVIRONMENT.is_production:
        deny_robots(ctx)


@task
def clean(ctx, revert=False):
    ctx.run("find . -name '*.pyc' -o -name 'generated-*' -delete -print")


@task(aliases=["dr"])
def deny_robots(ctx):
    dj(ctx, "setup_robots_txt --no-allow")


@task(aliases=["cs"])
def collectstatic(ctx, reload_uwsgi=False):
    dj(ctx, "collectstatic -c --noinput", pty=True)
    if reload_uwsgi:
        restart_uwsgi(ctx)


@task(aliases=["uindex"])
def update_index(ctx):
    dj(ctx, "update_index", pty=True)


@task(aliases=["restart"])
def restart_uwsgi(ctx):
    ctx.run("touch ./core/wsgi.py")


@task(aliases=["prep"], pre=[collectstatic, update_index], post=[restart_uwsgi])
def prepare(ctx):
    pass


@task(aliases=["qc"])
def quality_check_openabm_files_with_db(ctx):
    dj(ctx, "quality_check_files_with_db", pty=True)


@task
def sh(ctx, print_sql=False):
    dj(
        ctx,
        "shell_plus --ipython{}".format(" --print-sql" if print_sql else ""),
        pty=True,
    )


@task
def test(ctx, tests=None, coverage=False):
    if tests is not None:
        apps = tests
    else:
        apps = ""
    if coverage:
        ignored = [f"*{ignored_pkg}*" for ignored_pkg in env["coverage_omit_patterns"]]
        coverage_cmd = "coverage run --source={0} --omit={1}".format(
            ",".join(env["coverage_src_patterns"]), ",".join(ignored)
        )
    else:
        coverage_cmd = env["python"]
    ctx.run(
        f"{coverage_cmd} manage.py test {apps} --settings=core.settings.test",
        env={"DJANGO_SETTINGS_MODULE": "core.settings.test"},
    )


@task(pre=[call(test, coverage=True)])
def coverage(ctx):
    ctx.run("coverage html")


@task
def server(ctx, ip="0.0.0.0", port=8000):
    dj(ctx, f"runserver {ip}:{port}", capture=False)
