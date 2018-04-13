#!/bin/sh

chmod a+x /code/deploy/*.sh;

initdb() {
    cd /code;
    echo "Destroying and initializing database from scratch"
    /code/deploy/wait-for-it.sh db:5432 -- invoke db.init
}
initdb
/code/deploy/wait-for-it.sh elasticsearch:9200 -t 30 -- invoke docs.r

# without this css on gh-pages will not work
echo "Adding .nojekyll for css"
touch /code/docs/build/html/.nojekyll

# setup CNAME for DNS https://stackoverflow.com/questions/9082499/custom-domain-for-github-project-pages
echo "Adding CNAME"
echo docs.comses.net > /code/docs/build/html/CNAME
