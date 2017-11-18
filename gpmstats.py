from datetime import datetime

import click
from gmusicapi.clients import Mobileclient
from gmusicapi.exceptions import CallFailure


@click.group()
@click.option('--email', required=True)
@click.option('--password', prompt=True, hide_input=True, )
@click.pass_context
def cli(ctx, email, password):
    client = Mobileclient()
    if not client.login(email, password, Mobileclient.FROM_MAC_ADDRESS):
        raise click.ClickException('Username/password is incorrect.')
    ctx.obj['client'] = client
    ctx.obj['songs'] = client.get_all_songs()


def valid_year(ctx, param, value):
    if value and value > datetime.now().year:
        raise click.BadParameter(f'{value} is not a valid year.')
    return value


@click.command()
@click.option('--released-since', callback=valid_year, type=int)
@click.option('--released-in', callback=valid_year, type=int)
@click.option('--released-before', callback=valid_year, type=int)
@click.option('--include-singles', is_flag=True)
@click.option('--sort-by', type=click.Choice(['album', 'songs']), default='album')
@click.pass_context
def albums(ctx, released_since, released_in, released_before, include_singles, sort_by):
    client = ctx.obj['client']
    songs = ctx.obj['songs']

    if released_since:
        songs = filter(lambda s: s.get('year', released_since - 1) >= released_since, songs)
    elif released_in:
        songs = filter(lambda s: s.get('year') == released_in, songs)
    elif released_before:
        songs = filter(lambda s: (s.get('year') or (released_before + 1)) < released_before, songs)

    album_ids = filter(None, {song.get('albumId') for song in songs})
    albums = []
    for album_id in album_ids:
        try:
            album = client.get_album_info(album_id)
            if len(album['tracks']) > 1 or include_singles:
                albums.append(album)
        except CallFailure:
            continue

    def _sort_album(album):
        play_counts = [track.get('playCount', 0) for track in album['tracks']]
        if sort_by == 'album':
            return min(play_counts)
        elif sort_by == 'songs':
            return sum(play_counts)

    albums = sorted(albums, key=_sort_album, reverse=True)
    for album in albums:
        click.echo(f"{album['artist']} - {album['name']} ({album['year']})")


cli.add_command(albums)

if __name__ == '__main__':
    cli(obj={}, auto_envvar_prefix='GPM')
