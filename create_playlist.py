# Bug - It's only grabbing the first 5 songs in my liked songs on YouTube regardless of what songs are used
# Bug - It only works if there are only songs in the YouTube liked videos. If it comes across a video that is not a song, it will crash
# Need to fix
# Spotipy is a lightweight Python library for the Spotify Web API. With Spotipy, we can get full access to all of the music data provided by the Spotify platform.
import json #JSON stands for JavaScript Object Notation
#JSON is a lightweight format for storing and transporting data
#JSON is often used when data is sent from a server to a web page
import os #The OS module in Python provides a way of using operating system dependent functionality. 
#The functions that the OS module provides allows you to interface with the underlying operating system that Python is running on – be that Windows, Mac or Linux.

import google_auth_oauthlib.flow #This module provides integration with requests-oauthlib for running the OAuth 2.0 Authorization Flow and acquiring user credentials
import googleapiclient.discovery #Use the discovery module to build a Python representation of the API.
import googleapiclient.errors #Errors for the library.
import requests #Requests will allow you to send HTTP/1.1 requests using Python.
#It also allows you to access the response data of Python in the same way.
import youtube_dl # Command-line program to download videos from YouTube
from secrets import spotify_token, spotify_user_id


class CreatePlaylist:
    def __init__(self):
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}

    def get_youtube_client(self):
        #Log Into Youtube, taken from Youtube Data API

        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        # Oauth2 works through SSL layer. If your server is not parametrized to allow HTTPS, the fetch_token method 
        # will raise an oauthlib.oauth2.rfc6749.errors.InsecureTransportError. 
        # You can disable this check by the follwing:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets_file, scopes)
        credentials = flow.run_console()

        # from the Youtube DATA API
        youtube_client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=credentials)

        return youtube_client

    def get_liked_videos(self):
        #Grab Our Liked Videos & Create A Dictionary Of Important Song Information
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )
        response = request.execute() #to send the request, handling exceptions.

        # collect each video and get important information
        for item in response["items"]: #for loop through the dictionary values
            video_title = item["snippet"]["title"] #get the video title
            youtube_url = "https://www.youtube.com/watch?v={}".format(
                item["id"]) # get the youtube url by passing through the video id

            # use youtube_dl to collect the song name & artist name
            video = youtube_dl.YoutubeDL({}).extract_info(
                youtube_url, download=False)
            song_name = video["track"] # get the value of track i.e the song name
            artist = video["artist"] # get the value of artist i.e the artist name
            #It's only grabbing the first 5 songs in my liked songs
            if song_name is None and artist is None: #have to find a way to get the song name and artist
                split_title = video["title"].split(" ") #within the dictionary "video", there is a key called "title", this contains the song name and artist
                #split on the white-space
                i = 0
                artist = "" #artist is an empty string which we will add to
                while split_title[i] != "-": #Everything before the "-" is the artist
                    artist += split_title[i]
                    artist += " " #If the artist has a first and last name then we add a space between them
                    i += 1
                
                hyphen_index = split_title.index("-") #Find the index of the "-" so we can get the song which is everything after the hyphen
                j = hyphen_index + 1
                song_name = ""
                while j < len(split_title):
                    if split_title[j][0] == "[" or split_title[j][0] == "(" or split_title[j][0] == "{":
                        break #break if it comes across any brackets as this usually indicates that we have the song name at that point
                    song_name += split_title[j]
                    song_name += " "
                    j += 1

            if song_name is not None and artist is not None:
                # save all important info and skip any missing song and artist
                # Within this dictionary, the title of the song will be the key
                # and we let the value of the key equal to another dictionary containing the url, name and artist
                self.all_song_info[video_title] = {
                    "youtube_url": youtube_url,
                    "song_name": song_name,
                    "artist": artist,

                    # add the uri, easy to get song to put into playlist
                    "spotify_uri": self.get_spotify_uri(song_name, artist)

                }

    def create_playlist(self):
        #Create a new playlist in Spotify
        request_body = json.dumps({ #returns a string representing a json object from a dictionary
            "name": "Youtube Liked Songs",
            "description": "All Liked Youtube Videos",
            "public": True
        })

        query = "https://api.spotify.com/v1/users/{}/playlists".format( #This is the post request
            spotify_user_id)
        response = requests.post( #POST is used to send data to a server to create/update a resource
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        # playlist id
        return response_json["id"]

    def get_spotify_uri(self, song_name, artist):
        #Search for the song on Spotify
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=20".format(
            song_name,
            artist
        )
        response = requests.get( #GET is used to request data from a specified resource.
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]
        uri = songs[0]["uri"] # only use the first song
        return uri

    def add_song_to_playlist(self):
        # Add all liked songs into a new Spotify playlist
        # populate dictionary with our liked songs
        self.get_liked_videos()

        # collect all of uri
        uris = [info["spotify_uri"]
                for song, info in self.all_song_info.items()]

        # create a new playlist
        playlist_id = self.create_playlist()

        # add all songs into new playlist
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(
            playlist_id)

        response = requests.post(
            query,
            data=request_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )


if __name__ == '__main__':
    create_playlist = CreatePlaylist()
    create_playlist.add_song_to_playlist()