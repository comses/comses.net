#!/bin/sh

chmod a+x /code/deploy/*.sh;

initdb() {
    cd /code;
    echo "Destroying and initializing database from scratch"
    /code/deploy/wait-for-it.sh db:5432 -- invoke db.init
}
initdb
/code/deploy/wait-for-it.sh elasticsearch:9200 -t 30 -- invoke docs.r

# Add .nojekyll so that GiutHub will use Sphinx generated CSS
touch /docs/build/html/.nojekyll
# Add CNAME for custom domain. See https://stackoverflow.com/questions/9082499/custom-domain-for-github-project-pages
echo docs.comses.net > /docs/build/html/CNAME