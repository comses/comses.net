#!/usr/bin/env bash

/code/manage.py shell_plus <<-EOF
u = User.objects.get_or_create(
    username='__TEST_USER__',
    defaults=dict(first_name='Test', last_name='User', email='a@b.com'))
u.set_password('__CORE_COMSES_TEST_USER__')
u.save()
mp = MemberProfile.objects.get(user=u)
mp.institution = Institution.objects.get_or_create(name='ASU', url='https://www.asu.edu')
mp.save()
ea = EmailAddress.objects.get_or_create(user=u)
ea.verified = True
ea.set_as_primary(condiftional=True)
ea.save()
EOF