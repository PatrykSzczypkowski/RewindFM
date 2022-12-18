import pylast
import spotipy
import os
import sys
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime
from dateutil.relativedelta import relativedelta

USER = None if len(sys.argv) < 2 else sys.argv[1]  # "vesdd"
YEARS = None if len(sys.argv) < 3 else int(sys.argv[2])  # 1
DATE_STRING = None if len(sys.argv) < 4 else sys.argv[3]  # "31/10/2022"


class LastFMCredentials:
    API_KEY = os.getenv("LAST_FM_API_KEY")
    API_SECRET = os.getenv("LAST_FM_API_SECRET")


class SpotifyCredentials:
    CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
    CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


lastFM = pylast.LastFMNetwork(
    api_key=LastFMCredentials.API_KEY,
    api_secret=LastFMCredentials.API_SECRET
)

spotify = spotipy.Spotify(
    auth_manager=SpotifyOAuth(
        client_id=SpotifyCredentials.CLIENT_ID,
        client_secret=SpotifyCredentials.CLIENT_SECRET,
        redirect_uri="http://localhost",
        scope="playlist-modify-private,playlist-read-private"
    )
)


def convert_unix_timestamp_to_date_string(timestamp):
    return datetime.utcfromtimestamp(timestamp).strftime("%d/%m/%Y")


def get_start_of_day_timestamp_from_datetime(date, years=0):
    date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date = date - relativedelta(years=years)
    timestamp = int(date.timestamp())
    return timestamp


def create_spotify_playlist(name):
    spotify.user_playlist_create(spotify.me()['id'], name, public=False, description="Created by RewindFM")


def get_lastfm_tracks(timestamp, user):
    return lastFM.get_user(user).get_recent_tracks(limit=None, cacheable=True, time_from=timestamp,
                                                   time_to=timestamp + (24 * 60 * 60), stream=False,
                                                   now_playing=False)


def conver_lastfm_tracks_to_string_list(tracks):
    stripped_tracks = []
    for track in tracks:
        stripped_tracks.append(f"track:{track.track.title} artist:{track.track.artist.name}")

    return stripped_tracks


def remove_duplicate_lastfm_tracks(tracks, preserve_order=True):
    if preserve_order:
        # this shit weird and I don't get it
        seen = set()
        seen_add = seen.add
        return [x for x in tracks if not (x in seen or seen_add(x))]

    return set(tracks)  # pseudo randomize?


def get_spotify_track_ids(tracks):
    sp_track_id_list = []

    for track in tracks:
        sp_track = spotify.search(track)
        if len(sp_track['tracks']['items']) > 0:
            sp_track_id = sp_track['tracks']['items'][0]['id']
            sp_track_id_list.append(sp_track_id)

    return sp_track_id_list


def add_tracks_to_spotify_playlist(last_fm_tracks, playlist_id, allow_duplicates=False):
    tracks = conver_lastfm_tracks_to_string_list(last_fm_tracks)
    if allow_duplicates is False:
        tracks = remove_duplicate_lastfm_tracks(tracks)

    sp_track_id_list = get_spotify_track_ids(tracks)

    for i in range(0, len(sp_track_id_list), 100):
        start = 0 + i
        stop = 100 + i
        spotify.playlist_add_items(playlist_id, items=sp_track_id_list[start:stop])


def playlist_creator():
    # TODO: date ranges? a whole week of music a year ago
    if USER is None:
        raise Exception("USER not provided")
    if YEARS is None:
        raise Exception("YEARS not provided")

    if DATE_STRING is not None:
        # convert input string to datetime object
        user_date = datetime.strptime(DATE_STRING, "%d/%m/%Y")
        timestamp = get_start_of_day_timestamp_from_datetime(user_date)

    else:
        timestamp = get_start_of_day_timestamp_from_datetime(datetime.now(), YEARS)

    tracks = get_lastfm_tracks(timestamp, USER)
    if len(tracks) == 0:
        raise Exception("No scrobbles found for that day")

    date = convert_unix_timestamp_to_date_string(timestamp)
    create_spotify_playlist(date)
    playlists = spotify.current_user_playlists(limit=1)

    if len(playlists['items']) > 0:
        playlist_id = playlists['items'][0]['id']

    if playlist_id is not None:
        add_tracks_to_spotify_playlist(tracks, playlist_id, allow_duplicates=True)


def main():
    playlist_creator()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
