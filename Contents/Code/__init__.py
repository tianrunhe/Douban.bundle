DOUBAN_MOVIE_API_URL = "https://api.douban.com/v2/movie"
DOUBAN_MOVIE_SEARCH_URL = "{0}/{1}?q=%s".format(DOUBAN_MOVIE_API_URL, 'search')
DOUBAN_MOVIE_SUBJECT_URL = "{0}/{1}/%s".format(DOUBAN_MOVIE_API_URL, 'subject')


def Start():
    HTTP.Headers['User-Agent'] = (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10)'
        'AppleWebKit/600.1.25 (KHTML, like Gecko) Version/8.0 Safari/600.1.25'
    )


class DoubanAgent(Agent.Movies):
    name = 'Douban'
    languages = [Locale.Language.Chinese, Locale.Language.English]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    def search(self, results, media, lang):
        Log('*** Starting to query Douban: %s' % (media.name))
        if media.year is not None:
            search_str = String.Quote("{0} {1}".format(media.name, media.year))
        else:
            search_str = String.Quote(media.name)
        rt = JSON.ObjectFromURL(DOUBAN_MOVIE_SEARCH_URL % search_str)
        Log('*** Douban response: %s' % (rt))

        if rt['total'] == 0:
            Log('*** Did not find results with the movie name: %s and year: %s ***'
                % (media.name, media.year))
            return

        for i, movie in enumerate(rt['subjects']):
            if movie['subtype'] != 'movie':  # not a movie type, e.g., TV shows
                continue

            score = 90

            dist = abs(String.LevenshteinDistance(
                movie['title'].lower(),
                media.name.lower()))

            if movie['original_title'] != movie['title']:
                dist = min(abs(String.LevenshteinDistance(
                    movie['original_title'].lower(),
                    media.name.lower())), dist)

            score = score - dist

            # Adjust score slightly for 'popularity' (helpful for similar or
            # identical titles when no media.year is present)
            score = score - (5 * i)

            release_year = None
            if 'year' in movie and movie['year'] != '':
                try:
                    release_year = int(movie['year'])
                except:
                    pass

            media_year = None
            try:
                media_year = int(media.year)
            except:
                pass

            if media.year and media_year > 1900 and release_year:
                year_diff = abs(media_year - release_year)
                if year_diff <= 1:
                    score = score + 10
                else:
                    score = score - (5 * year_diff)

            if score <= 0:
                continue
            else:
                # All parameters MUST be filled in order for Plex find these
                # result.
                results.Append(MetadataSearchResult(
                    id=movie['id'],
                    name=movie['title'],
                    year=movie['year'],
                    lang=lang,
                    score=score))

    def update(self, metadata, media, lang):
        Log('*** Starting to fetch Douban with id: %s' % (metadata.id))
        m = JSON.ObjectFromURL(DOUBAN_MOVIE_SUBJECT_URL %
                               metadata.id, sleep=2.0)
        Log('*** Douban response: %s' % (m))

        metadata.rating = float(m['rating']['average'])
        metadata.title = m['title']
        metadata.original_title = m['original_title']
        metadata.summary = m['summary']

        # Genres
        metadata.genres.clear()
        for genre in m['genres']:
            metadata.genres.add(genre)

        # Countries
        metadata.countries.clear()
        for country in m['countries']:
            metadata.countries.add(country)

        # Directors
        metadata.directors.clear()
        for director in m['directors']:
            metadata.directors.add(director['name'])

        # Casts
        metadata.roles.clear()
        for cast in m['casts']:
            role = metadata.roles.new()
            role.name = cast['name']

        # Poster
        if len(metadata.posters.keys()) == 0:
            poster_url = m['images']['large']
            thumb_url = m['images']['small']
            metadata.posters[poster_url] = Proxy.Preview(
                HTTP.Request(thumb_url), sort_order=1)
