from flask import Flask, request, render_template, redirect, flash, url_for, abort
from sqlalchemy import or_, and_, not_
import json
import random
import string
import bcrypt
from flask_mail import Message
import datetime
import os
from hiketracker.models import Hike, User
import flask_login
from hiketracker.utils import (get_ip_addr, get_curr_loc, get_color_list, latlngarr_to_linestring, linestring_to_latlngarr,
                               latlng_to_point, miles_to_units, url_latlng_to_point, url_latlng_to_dict, units_to_miles,
                               pair_to_latlng, latlng_to_pair)
from hiketracker.app import app, Session

MAX_RESULTS = 10


# user loader for flask-login
@app.login_manager.user_loader
def user_loader(user_id):
    session = Session()
    user = session.query(User).filter_by(id=user_id).first()
    return user # should be None if user not in database


# login_manager for flask
@app.login_manager.request_loader
def request_loader(request):
    session = Session()
    email = request.form.get('email') # could have been request.form["email"]....should have been?
    user = session.query(User).filter_by(email=email).first()
    # should request_loader check if a person is authenticated?? or set that variable??
    return user
    # should


@app.route('/')
def hey_there():
    return "HI THERE!!!!  YOU'RE DOING A GREAT JOB--I CAN TELL<br>" \
           ""


@app.route('/email_me')
def email_me():
    msg = Message(
                  sender=app.config.get('MAIL_USERNAME'),
                  recipients=[os.environ.get('TEST_RECIPIENT_EMAIL')]
                  )
    msg.body = "Hello.  This is my test email. Sent at: " + str(datetime.datetime.now())
    msg.subject = "email from Hike Tracker"
    app.mail.send(msg)
    return "Email sent!!"


@app.route('/login', methods=['GET', 'POST'])
def login():
    next = request.args.get('next') or ""
    if request.method == 'GET':
        return '''

            <form action = "login?next='''+next+'''" method='POST'>
            <input type = 'text' name='email' id='email' placeholder='email'></input><br>
            <input type = 'submit' name='submit' value='Email Password'></input>
            </form>
            <span style='font-family: ariel, sans-serif; font-size: 12px'>New User?</span>
            <form action = "new_user?next='''+next+'''" method='GET'>
            <input type = 'submit' name='submit' value='Create new account'></input>
            </form>
            '''
    # POST
    # directed here from create new user, therefore form has name attribute
    if request.form.get("name"):
        session = Session()
        session.add(User(name=request.form["name"], email=request.form["email"]))
        session.commit()
    # send user an email with their password in it
    session = Session()
    user = session.query(User).filter_by(email=request.form["email"]).first()
    if user:
        # generate random password
        password = ''.join([random.SystemRandom().choice(string.digits + string.punctuation + string.ascii_letters)
                            for _ in range(random.SystemRandom().randint(15, 30))])
        # hash password and add to database
        user.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        # Note: password_time updates automatically when this is updated
        session.commit()
        msg = Message(

            sender=app.config.get('MAIL_USERNAME'),
            recipients=[user.email],
            subject="Hike Tracker login",
            body=password
            )
        msg.body = '''
        Hi '''+user.name+''',
        Here is your temporary password to log into our hike tracker website:
        ''' + password + '''
        Have a great day!
        The Hiker Trackers'''
        app.mail.send(msg)

        return '''
            <form action = "login_followup?next='''+next+'''" method='POST'>
            <input type = 'hidden' name='email' id='email' value="''' + user.email + '''">
            <input type = 'text' name='password' id='password' placeholder='password from email'></input>
            <input type = 'submit' name='submit' value='Login'></input>
            </form>
            '''
    else: # invalid email
        flash('invalid email')
        return redirect(url_for('login'))


@app.route('/login_followup', methods=['POST'])
def login_followup():
    submitted_password = request.form['password']
    submitted_email = request.form['email']
    session = Session()
    user = session.query(User).filter_by(email=submitted_email).first()
    if (user and user.email == submitted_email
        and bcrypt.checkpw(submitted_password.encode('utf-8'), user.password)
        and (datetime.datetime.now() - user.password_time).total_seconds() < 60*3): #three minutes
            flask_login.logout_user()
            flask_login.login_user(user)
            flash("You've been logged in")
            next = request.args.get('next')
            if not next_is_valid(next):
                return abort(400)
            return redirect(next or url_for('test_logged_in'))
    return redirect(url_for('test_logged_in'))

@app.route('/test')
def test():
    return redirect(url_for('hey_there'))

@app.route('/new_user', methods=['GET', 'POST'])
def add_new_user():
    next = request.args.get('next') or ""
    if request.method == 'GET':
        return '''
            <form action = "login?next='''+next+'''" method = 'POST' >
                <input type = 'text' name = 'name' id = 'name' placeholder = 'name' > </input >
                <input type = 'text' name = 'email' id = 'email' placeholder = 'email' > </input >
                <input type = 'submit' name = 'submit' value = 'Add User' > </input>
            </form >
        '''


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out'


def next_is_valid(url):
    return True


@app.route('/test_logged_in')
@flask_login.login_required
def test_logged_in():
    return 'Logged in as: ' + flask_login.current_user.email


@app.route('/add', methods=['GET', 'POST'])
@flask_login.login_required
def add_trail():
    if request.method == 'GET':
        ip_addr = get_ip_addr(request)
        curr_latlng = get_curr_loc(ip_addr) # dict
        return render_template('add.html', curr_latlng=curr_latlng)
    else: # POST
        session = Session()
        user = session.query(User).filter_by(id=flask_login.current_user.get_id()).first()
        # setting up kwargs for new_hike
        kwargs={
            "user_id" : user.id,
            "name" : request.form["trail_name"],
            "path" : latlngarr_to_linestring(json.loads(request.form["hike_coordinates"])),
            "difficulty" : request.form["difficulty"],
            "sun_shade" : request.form["sun_shade"],
            "surrounding_biome" : request.form.getlist("surrounding_biome"),
            "elevation" : request.form.getlist("elevation"),
            "trail_terrain" : request.form.getlist("trail_terrain"),
            "markings" : request.form["markings"]
        }
        ## old version (more efficient) of user_id query
        # user_id = session.query(User.id).filter_by(name=request.form["user_name"]).first()[0]

        new_hike = Hike(**kwargs)

        session.add(new_hike)
        session.commit()

        return "thanks, " + user.name + " for adding the " + request.form["trail_name"] + " trail with coords:\n " + \
               request.form["hike_coordinates"] + "\nfeel free to enter another"


@app.route('/search/advanced', methods=['GET', 'POST'])
@flask_login.login_required
def advanced_search():
    biomes = [['marsh', 'Marsh'], ['grassy', 'Grassy'], ['river', 'River/Creek'],
              ['wooded', 'Wooded'], ['near_water', 'Near Water'], ['mountain', 'Mountain'], ['desert', 'Desert'],
              ['view', 'Has a view']]

    elevations = [['flat', 'Flat'], ['hilly', 'Hilly'], ['mountains', 'Mountainous'], ['gradual_up', 'Gradual Uphill'],
                  ['steep_up', 'Steep Uphill'], ['gradual_down', 'Gradual Downhill'],
                  ['steep_down', 'Steep Downhill']]

    terrains = [['rocky', 'Rocky'], ['boulders', 'Boulders'], ['sandy', 'Sandy'], ['overgrown', 'High Grass'],
                ['water_crossings', 'Water Crossings'], ['paved', 'Paved'], ['trail', 'Dirt Trail'],
                ['bushwacking', 'No trail/Bushwacking']]

    if request.method == 'GET':
        return render_template('search.html', biomes=biomes, elevations=elevations, terrains=terrains)
    else:  # POST
        # get location from IP address
        ip_addr = get_ip_addr(request)
        curr_latlng = get_curr_loc(ip_addr)
        curr_latlng_point = latlng_to_point(curr_latlng)

        session = Session()
        query = session.query(Hike, Hike.path.ST_AsText())

        query = (query.filter(
            Hike.difficulty >= request.form["min_difficulty"],
            Hike.difficulty <= request.form["max_difficulty"],
            Hike.path.ST_Transform(2163).ST_Length() >= miles_to_units(float(request.form["min_distance"])),
            Hike.path.ST_Transform(2163).ST_Length() <= miles_to_units(float(request.form["max_distance"])),
            or_(Hike.sun_shade == request.form["sun_shade"], request.form["sun_shade"] == "don't care"),
            or_(len(request.form.getlist("markings")) == 0,  Hike.markings == "well_marked")
        )
        )

        for biome in biomes:
            query = query.filter(
                or_(request.form[biome[0]] == "don't care",
                    and_(request.form[biome[0]] == "yes", Hike.surrounding_biome.contains([biome[0]])),
                    and_(request.form[biome[0]] == "no", not_(Hike.surrounding_biome.contains([biome[0]])))
                    )
            )

        for elevation in elevations:
            query = query.filter(
                or_(request.form[elevation[0]] == "don't care",
                    and_(request.form[elevation[0]] == "yes", Hike.elevation.contains([elevation[0]])),
                    and_(request.form[elevation[0]] == "no", not_(Hike.elevation.contains([elevation[0]])))
                    )
            )

        for terrain in terrains:
            query = query.filter(
                or_(request.form[terrain[0]] == "don't care",
                    and_(request.form[terrain[0]] == "yes", Hike.trail_terrain.contains([terrain[0]])),
                    and_(request.form[terrain[0]] == "no", not_(Hike.trail_terrain.contains([terrain[0]])))
                    )
            )


        hike_results = query.order_by(Hike.path.ST_Distance(curr_latlng_point)).all()
        # no results
        if len(hike_results) == 0:
            return "No results; modify search"
        for hike, path in hike_results:
            hike.path_arr = linestring_to_latlngarr(path)  # json.dumps(linestring_to_latlngarr(path))
        colors = get_color_list(len(hike_results))
        return render_template('search_results.html',
                               hikes=[hike for (hike, path) in hike_results],
                               colors=colors,
                               curr_latlng=curr_latlng)


# search by hike length
@app.route('/search/length/<min_max>/<length>')
@flask_login.login_required
def get_paths_bylength(min_max, length):
    # search database for paths by length near user location
    session = Session()

    # get user's latlng
    ip_addr = get_ip_addr(request)
    curr_latlng = get_curr_loc(ip_addr)
    curr_latlng_point = latlng_to_point(curr_latlng)
    length_in_units = miles_to_units(float(length))
    initial_query = session.query(Hike, Hike.path.ST_AsText())

    if min_max == "min":
        ## OLD VERSION
        # query_with_comparison = initial_query.filter(Hike.path.ST_Length() >= float(length))
        # ST_Transform(ST_GeomFromText('LINESTRING(-72.1260 42.45, -72.123 42.1546)', 4326),2163)
        query_with_comparison = initial_query.filter(Hike.path.ST_Transform(2163).ST_Length() >= length_in_units)
    elif min_max == "max":
        query_with_comparison = initial_query.filter(Hike.path.ST_Transform(2163).ST_Length() <= length_in_units)
    else:
        return "Bad min_max parameter: use 'min' or 'max'"
    hike_results = query_with_comparison.order_by(Hike.path.ST_Distance(curr_latlng_point)).all()

    # no results
    if len(hike_results) == 0:
        return "No results; modify search"
    for hike, path in hike_results:
        hike.path_arr = linestring_to_latlngarr(path) # json.dumps(linestring_to_latlngarr(path))
    colors = get_color_list(len(hike_results))
    return render_template('search_results.html',
                           hikes=[hike for (hike, path) in hike_results],
                           colors=colors,
                           curr_latlng=curr_latlng)


@app.route('/search/user/<username>')
@flask_login.login_required
def get_paths_by_user(username):
    # get current location of user
    ip_addr = get_ip_addr(request)
    curr_latlng = get_curr_loc(ip_addr)
    curr_latlng_point = latlng_to_point(curr_latlng)
    # search database for paths entered by username
    session = Session()
    user = session.query(User).filter_by(name=username).first()
    if user:
        user_id = user.id
        hike_results = (session
                        .query(Hike, Hike.path.ST_AsText())
                        .filter_by(user_id=user_id)
                        .order_by(Hike.path.ST_Distance(curr_latlng_point))
                        .all())
        for hike, path in hike_results:
            hike.path_arr = linestring_to_latlngarr(path)
        colors = get_color_list(len(hike_results))
        return render_template('search_results.html', hikes=[hike for (hike, path) in hike_results], colors=colors,
                               curr_latlng=curr_latlng)
    return "bad user"



@app.route('/search/my_paths')
@flask_login.login_required
def get_my_paths():
    # get current location of user
    ip_addr = get_ip_addr(request)
    curr_latlng = get_curr_loc(ip_addr)
    curr_latlng_point = latlng_to_point(curr_latlng)
    # search database for paths entered by username
    session = Session()
    user = session.query(User).filter_by(id=flask_login.current_user.get_id()).first()
    if user:
        user_id = user.id
        hike_results = (session
                        .query(Hike, Hike.path.ST_AsText())
                        .filter_by(user_id=user_id)
                        .order_by(Hike.path.ST_Distance(curr_latlng_point))
                        .all())
        for hike, path in hike_results:
            hike.path_arr = linestring_to_latlngarr(path)
        colors = get_color_list(len(hike_results))
        return render_template('search_results.html', hikes=[hike for (hike, path) in hike_results], colors=colors,
                               curr_latlng=curr_latlng)
    return "Bad user"


# search by hike distance from "current location"
@app.route('/search/near/<latlng>')
@flask_login.login_required
def get_paths_by_location(latlng):
    #get latlng for searching
    search_latlng = url_latlng_to_dict(latlng)
    search_latlng_point = url_latlng_to_point(latlng)
    # search database for paths by length
    session = Session()
    hike_results = (session
                    .query(Hike, Hike.path.ST_AsText())
                    .order_by(Hike.path.ST_Distance(search_latlng_point))
                    .all())
    if hike_results:
        for hike, path in hike_results[:min(MAX_RESULTS, len(hike_results))]:
            hike.path_arr = linestring_to_latlngarr(path)  # json.dumps(linestring_to_latlngarr(path))
        colors = get_color_list(len(hike_results))
        return render_template('search_results.html',
                               hikes=[hike for (hike, path) in hike_results[:min(MAX_RESULTS, len(hike_results))]],
                               colors=colors,
                               curr_latlng=search_latlng)
    else:
        return 'Bad location'


# search by hikes that intersect with this hike
@app.route('/search/intersecting_hikes/<hike_name>')
@flask_login.login_required
def get_paths_by_intersection(hike_name):
    # search database for paths by length
    ip_addr = get_ip_addr(request)
    curr_latlng = get_curr_loc(ip_addr)
    curr_latlng_point = latlng_to_point(curr_latlng)
    session = Session()
    try:
        curr_hike = session.query(Hike).filter_by(name=hike_name).first()
        hike_results = (session
                        .query(Hike, Hike.path.ST_AsText())
                        .filter(Hike.path.ST_Intersects(curr_hike.path),
                                Hike.id != curr_hike.id)
                        .order_by(Hike.path.ST_Distance(curr_latlng_point))
                        .all())
        if hike_results:
            for hike, path in hike_results[:min(MAX_RESULTS, len(hike_results))]:
                hike.path_arr = linestring_to_latlngarr(path)
            colors = get_color_list(len(hike_results))
            return render_template('search_results.html',
                                   hikes=[hike for (hike, path) in hike_results[:min(MAX_RESULTS, len(hike_results))]],
                                   colors=colors,
                                   curr_latlng=curr_latlng)
        else:
            return 'No hikes intersect'
    except:
        return "bad hike name"


def test():
    return "You got me!!"
