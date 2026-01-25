import logging

from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from library.models import (
    ProgrammingLanguageTag,
    ProgrammingLanguage,
    ReleaseLanguage,
    CodebaseRelease,
    Codebase,
)


logger = logging.getLogger(__name__)

programming_languages = [
    {"name": "ABS", "url": "https://www.abs-lang.org", "is_pinned": False},
    {
        "name": "Assembly",
        "url": "https://en.wikipedia.org/wiki/Assembly_language",
        "is_pinned": False,
    },
    {"name": "C", "url": "https://www.c-language.org", "is_pinned": False},
    {
        "name": "C#",
        "url": "https://dotnet.microsoft.com/en-us/languages/csharp",
        "is_pinned": False,
    },
    {"name": "C++", "url": "https://isocpp.org", "is_pinned": False},
    {"name": "Common Lisp", "url": "https://common-lisp.net", "is_pinned": False},
    {"name": "Dart", "url": "https://dart.dev", "is_pinned": False},
    {"name": "Fortran", "url": "https://fortran-lang.org", "is_pinned": False},
    {"name": "Go", "url": "https://golang.org", "is_pinned": False},
    {"name": "Groovy", "url": "https://groovy-lang.org", "is_pinned": False},
    {"name": "Haskell", "url": "https://www.haskell.org", "is_pinned": False},
    {"name": "Java", "url": "https://www.oracle.com/java/", "is_pinned": True},
    {
        "name": "JavaScript",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        "is_pinned": False,
    },
    {"name": "Julia", "url": "https://julialang.org", "is_pinned": False},
    {"name": "Kotlin", "url": "https://kotlinlang.org", "is_pinned": False},
    {
        "name": "Logo",
        "url": "http://el.media.mit.edu/logo-foundation/logo/",
        "is_pinned": True,
    },
    {"name": "Lisp", "url": "https://lisp-lang.org", "is_pinned": False},
    {
        "name": "NetLogo",
        "url": "https://ccl.northwestern.edu/netlogo/",
        "is_pinned": True,
    },
    {
        "name": "Objective-C",
        "url": "https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/Introduction/Introduction.html",
        "is_pinned": False,
    },
    {"name": "PHP", "url": "https://www.php.net", "is_pinned": False},
    {"name": "Perl", "url": "https://www.perl.org", "is_pinned": False},
    {"name": "Python", "url": "https://www.python.org", "is_pinned": True},
    {"name": "R", "url": "https://www.r-project.org", "is_pinned": True},
    {"name": "Ruby", "url": "https://www.ruby-lang.org/en", "is_pinned": False},
    {"name": "Rust", "url": "https://www.rust-lang.org", "is_pinned": False},
    {"name": "Scala", "url": "https://www.scala-lang.org", "is_pinned": False},
    {"name": "Shell", "url": "https://www.gnu.org/software/bash/", "is_pinned": False},
    {"name": "Smalltalk", "url": "https://st.cs.uni-saarland.de", "is_pinned": False},
    {
        "name": "SQL",
        "url": "https://www.iso.org/standard/63555.html",
        "is_pinned": False,
    },
    {"name": "Swift", "url": "https://swift.org", "is_pinned": False},
    {"name": "TypeScript", "url": "https://www.typescriptlang.org", "is_pinned": False},
    {
        "name": "Visual Basic",
        "url": "https://docs.microsoft.com/en-us/dotnet/visual-basic/",
        "is_pinned": False,
    },
    {
        "name": "Wolfram Language",
        "url": "https://www.wolfram.com/language/",
        "is_pinned": False,
    },
]


class Command(BaseCommand):
    help = "Convert programming language tags to use the ReleaseLanguage model."

    def handle(self, *args, **options):
        ProgrammingLanguage.objects.all().delete()
        for lang in programming_languages:
            ProgrammingLanguage.objects.create(**lang)

        ReleaseLanguage.objects.all().delete()
        tags = ProgrammingLanguageTag.objects.all()
        aliases = {}
        for tag in tags:
            version = ""
            if tag.tag.name.lower().startswith("netlogo"):
                version = tag.tag.name[7:].strip()

            programming_language_name = tag.tag.name
            if tag.tag.name in aliases:
                programming_language_name = aliases[tag.tag.name]

            try:
                programming_language = ProgrammingLanguage.objects.get(name__iexact=programming_language_name)
            except ObjectDoesNotExist:
                programming_language = None

            if programming_language is None:
                programming_language_name = input("Enter the programming language name for tag '{}' (leave blank to skip): ".format(tag.tag.name))
                if programming_language_name == "":
                    logger.info("Skipping tag '{}'".format(tag.tag.name))
                    continue
                aliases[tag.tag.name] = programming_language_name

                programming_language = ProgrammingLanguage.objects.get_or_create(
                    name__iexact=programming_language_name,
                    defaults={"name": programming_language_name, "is_user_defined": True},
                )[0]

            ReleaseLanguage.objects.create(
                programming_language=programming_language,
                release=tag.content_object,
                version=version,
            )
