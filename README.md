# croawl [![Build Status](https://travis-ci.org/dissemin/croawl.svg)](https://travis-ci.org/dissemin/croawl)
Crawler to predict the availability of a full text at a given URL

Goal
----

[Bielefeld Academic Search Engine](https://www.base-search.net/) covers almost 100 million metadata records harvested
from open repositories. The problem is that for most of them, we have no idea whether they link to a full text or not.
For instance, [this item](https://repository.library.georgetown.edu/handle/10822/529311) does not seem to be associated with a
freely downloadable full text, whereas [this one](http://wrap.warwick.ac.uk/1742/) is.

The goal of this software is to perform this classification (not necessarily archiving the full texts when they are available,
just classifying the URLs into open / closed).

How this crawler works
----------------------

This crawler visits the URLs present in the OAI records stored by BASE.
If one of the URLs of the record points to a PDF file, we happily mark
the record as free to read.
Otherwise, we expect to land on an HTML page describing the paper,
such as [a HAL landing page](https://hal.archives-ouvertes.fr/hal-01164591).
We look for meta tags with metadata about the paper: sometimes it contains
a link to the full text (as required by the [Google Scholar inclusion guidelines](https://scholar.google.ch/intl/en/scholar/inclusion.html)). If this link actually
leads to a PDF, we mark the paper as free to read.
In all other cases, we consider the paper as unavailable.

Crawling 100 million URLs takes a lot of time, so we try to reduce the number of
requests we need to do. This is achieved by learning URL patterns to predict
the nature of a page without crawling it. For instance, we can learn
that `https://hal.archives-ouvertes.org/hal-[0-9]*/document` returns a PDF
file most of the time,
so when we see such an URL we consider it is a PDF file without actually
downloading it. This classifier is implemented in the `urltheory` module.

