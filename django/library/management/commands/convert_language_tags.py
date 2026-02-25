import logging
import re

from django.db.models import Count
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from library.models import (
    ProgrammingLanguageTag,
    ProgrammingLanguage,
    ReleaseLanguage,
)

logger = logging.getLogger(__name__)


def _alias_matches(alias, tag_name: str) -> bool:
    """alias: str (case-insensitive exact) or compiled regex."""
    if isinstance(alias, str):
        return tag_name.lower() == alias.lower()
    return bool(alias.search(tag_name))


def resolve_tag_to_language(tag_name: str, lang_list: list) -> tuple:
    """
    Return (language_name, version) or (None, "") if no match.
    name acts as first alias; aliases can be str (exact, case-insensitive) or compiled regex.
    """
    version = ""
    if tag_name.lower().startswith("netlogo"):
        version = tag_name[7:].strip()
    for lang in lang_list:
        name = lang["name"]
        if tag_name.lower() == name.lower():
            return (name, version)
        for a in lang.get("aliases", []):
            if _alias_matches(a, tag_name):
                return (name, version)
    return (None, "")


def _remove_duplicate_release_languages() -> None:
    """Remove non-versioned ReleaseLanguage when a versioned one exists (e.g. NetLogo + NetLogo 6.2)."""
    dupes = (
        ReleaseLanguage.objects.values("release", "programming_language")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
    )
    for d in dupes:
        rls = ReleaseLanguage.objects.filter(
            release_id=d["release"],
            programming_language_id=d["programming_language"],
        ).order_by("version")
        has_versioned = rls.exclude(version="").exists()
        if has_versioned:
            rls.filter(version="").delete()


programming_languages = [
    {
        "name": "ABS",
        "url": "https://www.abs-lang.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "C",
        "url": "https://www.c-language.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "C#",
        "url": "https://dotnet.microsoft.com/en-us/languages/csharp",
        "is_pinned": False,
        "aliases": [],
    },
    {"name": "C++", "url": "https://isocpp.org", "is_pinned": False, "aliases": []},
    {
        "name": "Common Lisp",
        "url": "https://common-lisp.net",
        "is_pinned": False,
        "aliases": [],
    },
    {"name": "Dart", "url": "https://dart.dev", "is_pinned": False, "aliases": []},
    {
        "name": "Fortran",
        "url": "https://fortran-lang.org",
        "is_pinned": False,
        "aliases": [],
    },
    {"name": "Go", "url": "https://golang.org", "is_pinned": False, "aliases": []},
    {
        "name": "Groovy",
        "url": "https://groovy-lang.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Haskell",
        "url": "https://www.haskell.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Java",
        "url": "https://www.oracle.com/java/",
        "is_pinned": True,
        "aliases": ["JDK 6", "JDK 1.7", "JDK 8", "Repast"],
    },
    {
        "name": "JavaScript",
        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Julia",
        "url": "https://julialang.org",
        "is_pinned": True,
        "aliases": ["julia-lang"],
    },
    {
        "name": "Kotlin",
        "url": "https://kotlinlang.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "NetLogo",
        "url": "https://ccl.northwestern.edu/netlogo/",
        "is_pinned": True,
        "aliases": ["Logo", "NetlLogo", re.compile(r"^netlogo", re.I)],
    },
    {
        "name": "Objective-C",
        "url": "https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/Introduction/Introduction.html",
        "is_pinned": False,
        "aliases": [],
    },
    {"name": "PHP", "url": "https://www.php.net", "is_pinned": False, "aliases": []},
    {"name": "Perl", "url": "https://www.perl.org", "is_pinned": False, "aliases": []},
    {
        "name": "Python",
        "url": "https://www.python.org",
        "is_pinned": True,
        "aliases": ["Pyton"],
    },
    {"name": "R", "url": "https://www.r-project.org", "is_pinned": True, "aliases": []},
    {
        "name": "Ruby",
        "url": "https://www.ruby-lang.org/en",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Rust",
        "url": "https://www.rust-lang.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Scala",
        "url": "https://www.scala-lang.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Shell",
        "url": "https://www.gnu.org/software/bash/",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Smalltalk",
        "url": "https://st.cs.uni-saarland.de",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "SQL",
        "url": "https://www.iso.org/standard/63555.html",
        "is_pinned": False,
        "aliases": [],
    },
    {"name": "Swift", "url": "https://swift.org", "is_pinned": False, "aliases": []},
    {
        "name": "TypeScript",
        "url": "https://www.typescriptlang.org",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Visual Basic",
        "url": "https://docs.microsoft.com/en-us/dotnet/visual-basic/",
        "is_pinned": False,
        "aliases": ["VBA", "Visual Basic Macro"],
    },
    {
        "name": "Wolfram Language",
        "url": "https://www.wolfram.com/language/",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "MATLAB",
        "url": "https://www.mathworks.com/products/matlab.html",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "LPL",
        "url": "",
        "is_user_defined": True,
        "is_pinned": False,
        "aliases": ["LPL 5.55"],
    },
    {
        "name": "GAML",
        "url": "https://gama-platform.org",
        "is_pinned": False,
        "aliases": ["GAMA"],
    },
    {
        "name": "ReLogo",
        "url": "https://repast.github.io/docs/ReLogoGettingStarted.pdf",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Mathematica",
        "url": "https://www.wolfram.com/mathematica/",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Cormas",
        "url": "https://cormas.org/",
        "is_pinned": False,
        "aliases": ["Cormas"],
    },
    {
        "name": "Arc Macro Language",
        "url": "",
        "is_pinned": False,
        "is_user_defined": True,
        "aliases": ["AML(Arc Macro Language)"],
    },
    {
        "name": "SeSAm",
        "url": "https://multiagentsimulation.com/",
        "is_pinned": False,
        "aliases": [],
    },
    {
        "name": "Stata",
        "url": "https://www.stata.com/",
        "is_pinned": False,
        "aliases": [],
    },
]


class Command(BaseCommand):
    help = "Convert programming language tags to use the ReleaseLanguage model."

    def handle(self, *args, **options):
        self.stdout.write(
            "This will delete all ProgrammingLanguage and all ReleaseLanguage rows, "
            "then repopulate from seed data and tags (initial migration only)."
        )
        confirm = input("Type 'y' to continue: ").strip().lower()
        if confirm != "y":
            self.stdout.write("Aborted.")
            return
        ProgrammingLanguage.objects.all().delete()
        for lang in programming_languages:
            db_lang = {k: v for k, v in lang.items() if k != "aliases"}
            ProgrammingLanguage.objects.create(**db_lang)

        ReleaseLanguage.objects.all().delete()
        tags = ProgrammingLanguageTag.objects.all()
        session_aliases = {}
        skip_forever = {
            "Allegro 80",
            "from",
            "ms visual studio 2010",
            "Jupyter Notebook",
            "hibernate",
            ">= 1.6",
            "agent based model (abm)",
            "Version 8, Update 141 (Build 1.8.0)",
            "Visual Studio 2013",
            "gis-based simulation",
            "Unity",
            "logic",
            "SciLab",
            "Any",
            "English",
            "ABM",
            "EnergyPlus",
            "PostGreSQL-PgAdminIII",
            "agent-based model",
            "VW7.6",
        }
        for tag in tags:
            if tag.tag.name in skip_forever:
                continue

            programming_language_name, version = resolve_tag_to_language(
                tag.tag.name, programming_languages
            )
            if programming_language_name is None and tag.tag.name in session_aliases:
                programming_language_name = session_aliases[tag.tag.name]

            if programming_language_name is None:
                programming_language_name = input(
                    f"Enter the programming language name for tag '{tag.tag.name}' ({tag.content_object.permanent_url}) (blank=skip once, '!'=always skip): "
                ).strip()
                if programming_language_name == "!":
                    skip_forever.add(tag.tag.name)
                    logger.info("Always skipping tag '%s'", tag.tag.name)
                    continue
                if programming_language_name == "":
                    logger.info("Skipping tag '%s'", tag.tag.name)
                    continue
                session_aliases[tag.tag.name] = programming_language_name

            try:
                programming_language = ProgrammingLanguage.objects.get(
                    name__iexact=programming_language_name
                )
            except ObjectDoesNotExist:
                programming_language = ProgrammingLanguage.objects.create(
                    name=programming_language_name,
                    is_user_defined=True,
                )

            ReleaseLanguage.objects.create(
                programming_language=programming_language,
                release=tag.content_object,
                version=version,
            )

        _remove_duplicate_release_languages()
