import re
from httplib import ResponseNotReady
from collections import Counter

from cl.celery import app
from cl.citations import find_citations, match_citations
from cl.citations.find_citations import SupraCitation
from cl.search.models import Opinion, OpinionsCited

# This is the distance two reporter abbreviations can be from each other if they
# are considered parallel reporters. For example, "22 U.S. 44, 46 (13 Atl. 33)"
# would have a distance of 4.
PARALLEL_DISTANCE = 4


@app.task
def identify_parallel_citations(citations):
    """Work through a list of citations and identify ones that are physically
    near each other in the document.

    Return a list of tuples. Each tuple represents a series of parallel
    citations. These will usually be length two, but not necessarily.
    """
    if len(citations) == 0:
        return citations
    citation_indexes = [c.reporter_index for c in citations]
    parallel_citation = [citations[0]]
    parallel_citations = set()
    for i, reporter_index in enumerate(citation_indexes[:-1]):
        if reporter_index + PARALLEL_DISTANCE > citation_indexes[i + 1]:
            # The present item is within a reasonable distance from the next
            # item. It's a parallel citation.
            parallel_citation.append(citations[i + 1])
        else:
            # Not close enough. Append what we've got and start a new list.
            if len(parallel_citation) > 1:
                if tuple(parallel_citation[::-1]) not in parallel_citations:
                    # If the reversed tuple isn't in the set already, add it.
                    # This makes sure a document with many references to the
                    # same case only gets counted once.
                    parallel_citations.add(tuple(parallel_citation))
            parallel_citation = [citations[i + 1]]

    # In case the last item had a citation.
    if len(parallel_citation) > 1:
        if tuple(parallel_citation[::-1]) not in parallel_citations:
            # Ensure the reversed tuple isn't in the set already (see above).
            parallel_citations.add(tuple(parallel_citation))
    return parallel_citations


@app.task
def get_document_citations(opinion):
    """Identify and return citations from the html or plain text of the
    opinion.
    """
    if opinion.html_columbia:
        citations = find_citations.get_citations(opinion.html_columbia)
    elif opinion.html_lawbox:
        citations = find_citations.get_citations(opinion.html_lawbox)
    elif opinion.html:
        citations = find_citations.get_citations(opinion.html)
    elif opinion.plain_text:
        citations = find_citations.get_citations(opinion.plain_text,
                                                 html=False)
    else:
        citations = []
    return citations


def create_cited_html(opinion, citations):
    if any([opinion.html_columbia, opinion.html_lawbox, opinion.html]):
        new_html = opinion.html_columbia or opinion.html_lawbox or opinion.html
        for citation in citations:
            if not citation.as_regex():
                continue
            new_html = re.sub(citation.as_regex(), citation.as_html(),
                              new_html)
    elif opinion.plain_text:
        inner_html = opinion.plain_text
        for citation in citations:
            if not citation.as_regex():
                continue
            repl = u'</pre>%s<pre class="inline">' % citation.as_html()
            inner_html = re.sub(citation.as_regex(), repl, inner_html)
        new_html = u'<pre class="inline">%s</pre>' % inner_html
    return new_html.encode('utf-8')


@app.task(bind=True, max_retries=5, ignore_result=True)
def update_document(self, opinion, index=True):
    """Get the citations for an item and save it and add it to the index if
    requested."""
    citations = get_document_citations(opinion)

    # First, match the naive Citation objects to actual Opinion objects
    try:
        citation_matches = get_citation_matches(opinion, citations)
    except ResponseNotReady as e:
        # Threading problem in httplib, which is used in the Solr query.
        raise self.retry(exc=e, countdown=2)

    # Next, consolidate duplicate matches, keeping a counter of how often each
    # match appears (so we know how many times an opinion cites another)
    # keys = opinion
    # values = number of time that opinion is cited
    grouped_matches = Counter(citation_matches)
    del grouped_matches[None]

    for matched_opinion in grouped_matches:
        # Increase citation count for matched cluster if it hasn't
        # already been cited by this opinion.
        if matched_opinion not in opinion.opinions_cited.all():
            matched_opinion.cluster.citation_count += 1
            matched_opinion.cluster.save(index=index)

    # Only update things if we found citations
    if citations:
        opinion.html_with_citations = create_cited_html(opinion, citations)

        # Nuke existing citations
        OpinionsCited.objects.filter(citing_opinion_id=opinion.pk).delete()

        # Create the new ones.
        OpinionsCited.objects.bulk_create([
            OpinionsCited(
                citing_opinion_id=opinion.pk,
                cited_opinion_id=matched_opinion.pk,
                depth=grouped_matches[matched_opinion]
            ) for matched_opinion in grouped_matches
        ])

    # Update Solr if requested. In some cases we do it at the end for
    # performance reasons.
    opinion.save(index=index)


def get_citation_matches(opinion, citations):
    # A list of opinions, as matched to citations
    citation_matches = []

    for i, citation in enumerate(citations):
        # If the citation is a "supra" citation, try to resolve it to one of
        # the citations that has already been matched
        if isinstance(citation, SupraCitation):
            for op in citation_matches[0:i]:
                # The only data point for resolution that we have is the guess
                # at what the "supra" citation's antecedent is. This is usually
                # an abbreviated form of the plaintiff, so that guess is stored
                # in that field and we compare it to the known case names of
                # the already matched opinions.
                if citation.plaintiff in op.cluster.case_name_full:
                    # Just use the first one found, since we have no way
                    # to make a principled choice between candidates.
                    # If nothing is found, then the "supra" reference is
                    # effectively dropped.
                    citation_matches.append(op)
                    break

        # Otherwise, the citation is just a regular citation, so try to match
        # it directly to an opinion
        else:
            matches = match_citations.match_citation(
                citation,
                citing_doc=opinion
            )

            if len(matches) == 1:
                match_id = matches[0]['id']
                try:
                    matched_opinion = Opinion.objects.get(pk=match_id)
                    citation_matches.append(matched_opinion)

                    # Set the match fields on the original citation object
                    # so that they can later be used for generating inline html
                    citation.match_url = matched_opinion.cluster.get_absolute_url()
                    citation.match_id = matched_opinion.pk
                except Opinion.DoesNotExist:
                    # No Opinions returned. Press on.
                    continue
                except Opinion.MultipleObjectsReturned:
                    # Multiple Opinions returned. Press on.
                    continue
            else:
                # No match found for citation
                continue

    return citation_matches


@app.task(ignore_result=True)
def update_document_by_id(opinion_id, index=True):
    op = Opinion.objects.get(pk=opinion_id)
    update_document(op, index=index)
