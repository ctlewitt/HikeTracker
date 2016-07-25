from sqlalchemy.dialects.postgresql import ARRAY, ENUM
from sqlalchemy import cast, Column, Integer, String, ForeignKey
from sqlalchemy.types import Enum, DateTime, Binary
import enum
import re
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry
import flask_login
import datetime


Base = declarative_base()


# taken from SLQAlchemy docs:
# http://docs.sqlalchemy.org/en/latest/dialects/postgresql.html#using-enum-with-array
class ArrayOfEnum(ARRAY):
    def bind_expression(self, bindvalue):
        return cast(bindvalue, self)  #was sa.cast
    def result_processor(self, dialect, coltype):
        super_rp = super(ArrayOfEnum, self).result_processor(
            dialect, coltype)
        def handle_raw_string(value):
            inner = re.match(r"^{(.*)}$", value).group(1)
            return inner.split(",") if inner else []
        def process(value):
            if value is None:
                return None
            return super_rp(handle_raw_string(value))
        return process

class ShadeSun(enum.Enum):
    shade = "shade"
    sun = "sun"
    mixed = "mixed"


#for use in ArrayOfEnum
class SurroundingBiome(enum.Enum):
    rocky = "rocky"
    marsh = "marsh"
    grassy = "grassy"
    river = "river"
    wooded = "wooded"
    near_water = "near_water"
    mountain = "mountain"
    desert = "desert"
    view = "view"

#for use in ArrayOfEnum
class Elevation(enum.Enum):
    flat = "flat"
    hilly = "hilly"
    mountains = "mountains"
    gradual_up = "gradual_up"
    steep_up = "steep_up"
    gradual_down = "gradual_down"
    steep_down = "steep_down"

# for use in ArrayOfEnum
class TrailTerrain(enum.Enum):
    rocky = "rocky"
    boulders = "boulders"
    sandy = "sandy"
    overgrown = "overgrown"
    water_crossings = "water_crossings"
    paved = "paved"
    trail = "trail"
    bushwacking = "bushwacking"

class Markings(enum.Enum):
    well_marked = "well_marked"
    poorly_marked = "poorly_marked"
    n_a = "n_a"



class Hike(Base):
   __tablename__ = "hikes"
   id = Column(Integer, primary_key=True)
   #many to one relationship with User
   user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
   name = Column(String, nullable=False)
   path = Column(Geometry('LINESTRING', 4326), nullable=False)
   difficulty = Column(Integer, nullable=False)
   sun_shade = Column(Enum(ShadeSun), nullable=False)
   surrounding_biome = Column(ArrayOfEnum(Enum(SurroundingBiome)), nullable=False)
   elevation = Column(ArrayOfEnum(Enum(Elevation)), nullable=False)
   trail_terrain = Column(ArrayOfEnum(Enum(TrailTerrain)), nullable=False)
   markings = Column(Enum(Markings), nullable=False)
   user = relationship("User", back_populates="hikes")


class User(Base, flask_login.UserMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, nullable=False)
    phone = Column(Integer)
    hikes = relationship("Hike", back_populates="user")
    #password = Column(String)
    password = Column(Binary(60))
    password_time = Column(DateTime, onupdate=datetime.datetime.now)


