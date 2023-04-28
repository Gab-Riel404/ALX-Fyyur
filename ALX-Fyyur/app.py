#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import (
    Flask, 
    render_template, 
    request, 
    Response, 
    flash, 
    redirect, 
    url_for,
    abort
)
from flask_moment import Moment
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from datetime import datetime, timezone
from sqlalchemy import or_, desc
import sys
import pytz
from models import db, Artist, Venue, Show

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db.init_app(app)
migrate = Migrate(app, db)


#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format, locale='en')

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO: replace with real venues data.
  #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue.
  locals = []
  #utc=pytz.UTC
  current_date = datetime.now()
  venues = Venue.query.all()
  places = Venue.query.distinct(Venue.city, Venue.state).all()
  for place in places:
      locals.append({
          'city': place.city,
          'state': place.state,
          'venues': [{
              'id': venue.id,
              'name': venue.name,
              'num_upcoming_shows': len([show for show in venue.shows if show.start_time > current_date])
          } for venue in venues if
              venue.city == place.city and venue.state == place.state]
      })
  return render_template('pages/venues.html', areas=locals)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  term = request.form.get('search_term')
  search = "%{}%".format(term.lower())
  res= Venue.query.filter(or_(Venue.name.ilike(search), Venue.city.ilike(search), Venue.state.ilike(search))).all()
  response = {'count':len(res),'data':res}
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id
  venue = Venue.query.get_or_404(venue_id)
  past_shows = []
  upcoming_shows = []
  for show in venue.shows:
      temp_show = {
          'artist_id': show.artist_id,
          'artist_name': show.artist.name,
          'artist_image_link': show.artist.image_link,
          'start_time': show.start_time.strftime("%m/%d/%Y, %H:%M")
      }
      
      #utc=pytz.UTC
      #show_time = show.start_time
      current_date = datetime.now()
      
      if current_date < show.start_time:
          upcoming_shows.append(temp_show)
      else:
          past_shows.append(temp_show)

  # object class to dict
  data = vars(venue)

  data['past_shows'] = past_shows
  data['upcoming_shows'] = upcoming_shows
  data['past_shows_count'] = len(past_shows)
  data['upcoming_shows_count'] = len(upcoming_shows)
  
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion
  error = False
  form = VenueForm(request.form, meta={'csrf': False})
  if form.validate():
    try:
      venue = Venue(
          name=form.name.data,
          genres=form.genres.data,
          address=form.address.data,
          city=form.city.data,
          state=form.state.data,
          phone=form.phone.data,
          facebook_link=form.facebook_link.data,
          image_link=form.image_link.data,
          website=form.website_link.data,
          seeking_talent=form.seeking_talent.data,
          seeking_description=form.seeking_description.data
      )
      db.session.add(venue)
      db.session.commit()
    except ValueError as e:
        print(e)
        error = True
        # If there is any error, roll it back
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if not error:
        flash('Venue ' + request.form.get('name') + ' was successfully listed!')
    else:
      flash('An error occurred. Venue ' + request.form.get('name') + ' could not be listed.')
      abort(500)
# If there is any invalid field
  else:
      message = []
      for field, err in form.errors.items():
          message.append(field + ' ' + '|'.join(err))
      flash('Errors ' + str(message))
      return render_template('forms/new_venue.html', form=form)
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>/delete', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a artist_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  error = False
  existing_venue = Venue.query.filter_by(id=venue_id).one_or_none()
  if not existing_venue:
        return json.dumps({
          'success':
              False,
          'error':
              'Venue #' + venue_id + ' not found'
      }), 404
  else:
    try:
      Show.query.filter_by(venue_id=venue_id).delete()
      Venue.query.filter_by(id=venue_id).delete()
      db.session.commit()
    except ValueError as e:
      print(e)
      error=True
      db.session.rollback()
      #flash('An error occurred deleting the Artist')
    finally:
      db.session.close()
    if not error:
      flash('Venue successfully deleted!')
    else:
      flash('An error occurred. Venue could not be deleted.')
      abort(500)
    return render_template('pages/home.html')

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database
  data=[]
  artists = db.session.query(Artist).order_by('id').all()
  for artist in artists:   
      data.append({
          "id":artist.id,
          "name":artist.name,
          })
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  term = request.form.get('search_term')
  search = "%{}%".format(term.lower())
  res= Artist.query.filter(or_(Artist.name.ilike(search), Artist.city.ilike(search), Artist.state.ilike(search))).all()
  response = {'count':len(res),'data':res}
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
      # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artist table, using artist_id
  artist = Artist.query.get_or_404(artist_id)
  past_shows = []
  upcoming_shows = []
  for show in artist.shows:
      artist_show = {"venue_id": show.venue_id,
                      "venue_name": show.venue.name,
                      "venue_image_link": show.venue.image_link,
                      'start_time': show.start_time.strftime("%m/%d/%Y, %H:%M")
                      }
      
      #utc=pytz.UTC
      current_date = datetime.now()
      show_time = show.start_time
      
      if current_date < show_time:
          upcoming_shows.append(artist_show)
      else:
          past_shows.append(artist_show)

  # object class to dict
  data = vars(artist)
  
  data['past_shows'] = past_shows
  data['upcoming_shows'] = upcoming_shows
  data['past_shows_count'] = len(past_shows)
  data['upcoming_shows_count'] = len(upcoming_shows)

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.get_or_404(artist_id)
  form.name.data=artist.name
  form.genres.data=artist.genres
  form.city.data=artist.city
  form.state.data=artist.state
  form.phone.data=artist.phone
  form.facebook_link.data=artist.facebook_link
  form.image_link.data=artist.image_link
  form.website_link.data=artist.website
  form.seeking_venue.data=artist.seeking_venue
  form.seeking_description.data=artist.seeking_description
  
  # TODO: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  error = False
  artist = Artist.query.filter_by(id=artist_id).one_or_none()
  form = ArtistForm(request.form, meta={'csrf': False})
  if not artist:
    return json.dumps({
        'success':
            False,
        'error':
            'Artist #' + artist_id + ' not found'
    }), 404
  else:
    if form.validate():
      artist.name=form.name.data or artist.name
      artist.genres=form.genres.data or artist.genre
      artist.city=form.city.data or artist.city
      artist.state=form.state.data or artist.state
      artist.phone=form.phone.data or artist.phone
      artist.facebook_link=form.facebook_link.data or artist.facebook_link
      artist.image_link=form.image_link.data or artist.image_link
      artist.website=form.website_link.data or artist.website
      artist.seeking_venue=form.seeking_venue.data or artist.seeking_venue
      artist.seeking_description=form.seeking_description.data or artist.seeking_description
      try:
        db.session.commit()
      except ValueError as e:
        print(e)
        error = True
        db.session.rollback()
        #print(sys.exc_info())
      finally:
        db.session.close()
      if not error:
        flash('Artist ' + request.form.get('name') + ' was successfully updated!')
      else:
        flash('An error occurred. Artist ' + request.form.get('name') + ' could not be updated.')
        abort(500)
    else:
        message = []
        for field, err in form.errors.items():
            message.append(field + ' ' + '|'.join(err))
        flash('Errors ' + str(message))
        abort(500)
    return redirect(url_for('show_artist', artist_id=artist_id))
  

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  form = VenueForm()
  venue = Venue.query.get_or_404(venue_id)
  form.name.data=venue.name
  form.genres.data=venue.genres
  form.address.data=venue.address
  form.city.data=venue.city
  form.state.data=venue.state
  form.phone.data=venue.phone
  form.facebook_link.data=venue.facebook_link
  form.image_link.data=venue.image_link
  form.website_link.data=venue.website
  form.seeking_talent.data=venue.seeking_talent
  form.seeking_description.data=venue.seeking_description
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  error = False
  form = VenueForm(request.form, meta={'csrf': False})
  if form.validate():
    try:
      venue = Venue(
          name=form.name.data,
          genres=form.genres.data,
          address=form.address.data,
          city=form.city.data,
          state=form.state.data,
          phone=form.phone.data,
          facebook_link=form.facebook_link.data,
          image_link=form.image_link.data,
          website=form.website_link.data,
          seeking_talent=form.seeking_talent.data,
          seeking_description=form.seeking_description.data
      )
      db.session.add(venue)
      db.session.commit()
    except ValueError as e:
        print(e)
        error = True
        db.session.rollback()
        #print(sys.exc_info())
    finally:
      db.session.close()
    
    if not error:
        flash('Venue ' + request.form.get('name') + ' was successfully updated!')
    else:
      flash('An error occurred. Venue ' + request.form.get('name') + ' could not be updated.')
      abort(500)
  else:
      message = []
      for field, err in form.errors.items():
          message.append(field + ' ' + '|'.join(err))
      flash('Errors ' + str(message))
      return render_template('forms/edit_venue.html', form=form, venue=venue)
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion
  error = False
  form = ArtistForm(request.form, meta={'csrf': False})
  if form.validate():
    try:
      artist = Artist(
        name=form.name.data,
        genres=form.genres.data,
        city=form.city.data,
        state=form.state.data,
        phone=form.phone.data,
        facebook_link=form.facebook_link.data,
        image_link=form.image_link.data,
        website=form.website_link.data,
        seeking_venue=form.seeking_venue.data,
        seeking_description=form.seeking_description.data 
      )
      db.session.add(artist)
      db.session.commit()
    except ValueError as e:
      print(e)
      error = True
      db.session.rollback()
      #print(sys.exc_info())
    finally:
      db.session.close()
    if not error:
      flash('Artist ' + request.form.get('name') + ' was successfully listed!')
    else:
      flash('An error occurred. Artist ' + request.form.get('name') + ' could not be listed.')
      abort(500)
  else:
      message = []
      for field, err in form.errors.items():
          message.append(field + ' ' + '|'.join(err))
      flash('Errors ' + str(message))
      return render_template('forms/new_artist.html', form=form)
  return render_template('pages/home.html')


@app.route('/artists/<artist_id>/delete', methods=['DELETE'])
def delete_artist(artist_id):
  # TODO: Complete this endpoint for taking a artist_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  error = False
  existing_artist = Artist.query.filter_by(id=artist_id).one_or_none()
  if not existing_artist:
        return json.dumps({
          'success':
              False,
          'error':
              'Artist #' + artist_id + ' not found'
      }), 404
  else:
    try:
      Show.query.filter_by(artist_id=artist_id).delete()
      Artist.query.filter_by(id=artist_id).delete()
      db.session.commit()
    except ValueError as e:
      print(e)
      error=True
      db.session.rollback()
      #flash('An error occurred deleting the Artist')
    finally:
      db.session.close()
    if not error:
      flash('Artist successfully deleted!')
    else:
      flash('An error occurred. Artist could not be deleted.')
      abort(500)
  return render_template('pages/home.html')
    

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  data = []
  shows = db.session.query(Show).order_by(desc(Show.start_time)).all()
  for show in shows:
        artist = db.session.query(Artist.name, Artist.image_link).filter(Artist.id == show.artist_id).one()
        venue = db.session.query(Venue.name).filter(Venue.id == show.venue_id).one()
        data.append({
          "venue_id": show.venue_id,
          "venue_name": venue.name,
          "artist_id": show.artist_id,
          "artist_name":artist.name,
          "artist_image_link": artist.image_link,
          "start_time": show.start_time.strftime('%m/%d/%Y')
        })
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead
  error=False
  try:
    data = Show()
    data.venue_id = request.form.get('venue_id')
    data.artist_id = request.form.get('artist_id')
    data.start_time = request.form.get('start_time')
    db.session.add(data)
    db.session.commit()
  except:
    error=True
    db.session.rollback()
    print(sys.exc_info())
  finally:
    db.session.close()
  if not error:
    flash('Show was successfully listed!')
  else:
    flash('An error occurred. Show could not be listed.')
    abort(500)
  # TODO: on unsuccessful db insert, flash an error instead.
  # e.g., flash('An error occurred. Show could not be listed.')
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
