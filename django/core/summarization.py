from textwrap import shorten

import jinja2
from sumy.nlp.stemmers import Stemmer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.html import HtmlParser
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.utils import get_stop_words

from .utils import markdown_to_sanitized_html

LANGUAGE = 'english'
SENTENCES_COUNT = 6

stemmer = Stemmer(LANGUAGE)
summarizer = LuhnSummarizer(stemmer)
summarizer.stop_words = get_stop_words(LANGUAGE)

template = jinja2.Template('''
{% for sentence in sentences %}
<p>{{ sentence }}</p>
{% endfor %}''')


def summarize(md: str, sentences_count=5):
    sanitized_html = markdown_to_sanitized_html(md)
    parser = HtmlParser.from_string(sanitized_html, url=None, tokenizer=Tokenizer(LANGUAGE))
    summary = template.render(sentences=[' '.join(sentence.words) for sentence
                              in summarizer(parser.document, sentences_count)])
    return summary


def summarize_to_text(md: str, sentences_count, max_length=300):
    sanitized_html = markdown_to_sanitized_html(md)
    parser = HtmlParser.from_string(sanitized_html, url=None, tokenizer=Tokenizer(LANGUAGE))
    summary = '\n\n'.join(' '.join(sentence.words) for sentence in summarizer(parser.document, sentences_count))
    if max_length is not None:
        return shorten(summary, width=max_length)
    return summary