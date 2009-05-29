###
### Copyright 2009 The Chicago Independent Radio Project
### All Rights Reserved.
###
### Licensed under the Apache License, Version 2.0 (the "License");
### you may not use this file except in compliance with the License.
### You may obtain a copy of the License at
###
###     http://www.apache.org/licenses/LICENSE-2.0
###
### Unless required by applicable law or agreed to in writing, software
### distributed under the License is distributed on an "AS IS" BASIS,
### WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
### See the License for the specific language governing permissions and
### limitations under the License.
###

"""Data model for CHIRP's DJ database."""

from google.appengine.ext import db


class DjDbImage(db.Model):
    """An image (usually a JPEG or PNG) associated with an artist or album.

    Images are uniquely defined by their SHA1 checksums.

    Attributes:
      image_data: A binary blob containing the image data.
      image_mimetype: A string that describes the image's mimetype.
    """

    image_data = db.BlobProperty(required=True)

    image_mimetype = db.StringProperty(required=True)

    _KEY_PREFIX = u"djdb/img:"

    @classmethod
    def get_key_name(cls, sha1):
        """Returns the datastore key name based on the image's SHA1."""
        return cls._KEY_PREFIX + sha1

    def __init__(self, *args, **kwargs):
        """Constructor.

        If necessary, automatically sets the entity's key according
        to our standard scheme.
        """
        if 'sha1' in kwargs:
            assert 'key_name' not in kwargs
            kwargs['key_name'] = self.get_key_name(kwargs['sha1'])
        db.Model.__init__(self, *args, **kwargs)

    @property
    def sha1(self):
        """Returns the image's SHA1 checksum."""
        return self.key().name()[len(self._KEY_PREFIX):]

    URL_PREFIX = "/djdb/image/"

    @property
    def url(self):
        """Returns a URL that can be used to retrieve this image."""
        return self.URL_PREFIX + self.sha1

    @classmethod
    def get_by_url(cls, url):
        """Fetches an image from the datastore by URL.

        Returns None if no matching image can be found.
        """
        i = url.find(cls.URL_PREFIX)
        if i == -1:
            return None
        sha1 = url[i + len(cls.URL_PREFIX):]
        key_name = cls.get_key_name(sha1)
        return cls.get_by_key_name(key_name)


class Artist(db.Model):
    """An individual musician, or a band.

    These entities are uploaded directly from the CHIRP music library
    database, which is considered to be authoritative.

    Attributes:
      name: The canonical name used to describe this artist in TPE1 tags.
        This name should follow the music committee's naming style guide.
      image: An image associated with this artist.
    """
    name = db.StringProperty(required=True)

    image = db.ReferenceProperty(DjDbImage)

    # TODO(trow): Add a list of references to related artists?

    def __unicode__(self):
        return self.name


class Album(db.Model):
    """An album in CHIRP's digital library.

    An album consists of a series of numbered tracks.

    Attributes:
      title: The name of the album.  This is used in TALB tags.
      album_id: A unique integer identifier that is assigned to the
        album when it is imported into the music library.
      import_timestamp: When this album was added to the library.
      is_compilation: If True, this album is a compilation and
        contains songs by many different artists.
      album_artist: A reference to the Artist entity of the creator
        of this album.  This attribute is set if and only if
        'is_compilation' is False.
      num_tracks: The number of tracks on this album.
      image: An image associated with this album.  This is typically
        used for the album's cover art.
    """
    title = db.StringProperty(required=True)

    album_id = db.IntegerProperty(required=True)

    import_timestamp = db.DateTimeProperty(required=True)

    is_compilation = db.BooleanProperty(required=False, default=False)

    album_artist = db.ReferenceProperty(Artist, required=False)

    num_tracks = db.IntegerProperty(required=True)

    image = db.ReferenceProperty(DjDbImage)

    # Keys are automatically assigned.  This key format makes uploading
    # albums to the datastore an idempotent operation.
    _KEY_FORMAT = u"djdb/a:%x"

    @classmethod
    def get_key_name(cls, album_id):
        """Generate the datastore key for an Album entity."""
        return cls._KEY_FORMAT % album_id

    def __init__(self, *args, **kwargs):
        """Constructor.

        If necessary, automatically sets the entity's key according
        to our standard scheme.
        """
        if 'key_name' not in kwargs:
            kwargs['key_name'] = self.get_key_name(kwargs['album_id'])
        db.Model.__init__(self, *args, **kwargs)

    def __unicode__(self):
        return self.title

    _COMPILATION_ARTIST_NAME = u"Various Artists"

    _MISSING_ARTIST_NAME = u"*MISSING ARTIST*"

    @property
    def artist_name(self):
        """Returns a human-readable string describing the album's creator."""
        if self.is_compilation:
            return self._COMPILATION_ARTIST_NAME
        return ((self.album_artist and self.album_artist.name)
                or self._MISSING_ARTIST_NAME)

    @property
    def sorted_tracks(self):
        """Returns Album tracks sorted by track number."""
        return sorted(self.track_set, key=lambda x: x.track_num)


_CHANNEL_CHOICES = ("stereo", "joint_stereo", "dual_mono", "mono")


class Track(db.Model):
    """A track in CHIRP's digital library.

    Each track's audio content is stored in a separate MP3 file in
    the digital library.

    Attributes:
      album: A reference to the Album entity that this track is a part of.
      title: The name of the track, as stored in the MP3 file's TIT2 tag.
      track_artist: A reference to the Artist entity of the track's creator.
        This must be set if self.album.is_compilation is True.
        It may be set if self.album.is_compilation is False.
      sampling_rate_hz: The sampling rate of the track's MP3 file, measured
        in Hertz.
      bit_rate_kbps: The bit rate of the MP3 file, measured in kbps (kilobits
        per second).
      channels: The number and type of channels in the MP3 file.
      duration_ms: The duration of the track, measured in milliseconds.
        (Remember that 1 second = 1000 milliseconds!)
    """
    album = db.ReferenceProperty(Album, required=True)

    title = db.StringProperty(required=True)

    track_artist = db.ReferenceProperty(required=False)

    # TODO(trow): Validate that this is > 0 and <= self.album.num_tracks.
    track_num = db.IntegerProperty(required=True)

    sampling_rate_hz = db.IntegerProperty(required=True)

    bit_rate_kbps = db.IntegerProperty(required=True)

    channels = db.CategoryProperty(required=True, choices=_CHANNEL_CHOICES)

    # TODO(trow): Validate that this is > 0.
    duration_ms = db.IntegerProperty(required=True)

    @property
    def duration(self):
        """A human-readable version of the track's duration."""
        dur_ms = self.duration_ms % 1000
        dur_s = ((self.duration_ms - dur_ms) // 1000) % 60
        dur_m = (self.duration_ms - dur_ms - 1000*dur_s) // 60000
        return "%d:%02d" % (dur_m, dur_s)

    @property
    def artist_name(self):
        """Returns a string containing the name of the track's creator."""
        return ((self.track_artist and self.track_artist.name)
                or self.album.artist_name)

    _KEY_PREFIX = u"djdb/t:"

    @classmethod
    def get_key_name(cls, ufid):
        """Returns the datastore key name based on the track's UFID."""
        return cls._KEY_PREFIX + ufid

    def __init__(self, *args, **kwargs):
        """Constructor.

        If necessary, automatically sets the entity's key according
        to our standard scheme.
        """
        if 'ufid' in kwargs:
            assert 'key_name' not in kwargs
            kwargs['key_name'] = self.get_key_name(kwargs['ufid'])
        db.Model.__init__(self, *args, **kwargs)

    @property
    def ufid(self):
        """Returns the library UFID of the track's MP3."""
        return self.key().name()[len(self._KEY_PREFIX):]

    def __unicode__(self):
        return self.title


class SearchMatches(db.Model):
    # What generation is this data a part of?  In the future we can use
    # this for development, schema changes, reindexing, etc.
    generation = db.IntegerProperty(required=True)

    # The name of the entity type.  In practice, the string returned by
    # my_obj.key().kind().
    entity_kind = db.StringProperty(required=True)

    # A normalized search term.
    term = db.StringProperty(required=True)

    # When this chunk of matches was added.
    timestamp = db.DateTimeProperty(auto_now=True)

    # A list of datastore keys for objects whose text metadata contains
    # the term "term".
    matches = db.ListProperty(db.Key)
    

    
