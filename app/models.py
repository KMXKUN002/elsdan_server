from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql.schema import ForeignKey

from app import db


class User(db.Model):
    __tablename__ = 'oc_users'
    __table_args__ = {'extend_existing': True}

    uid = Column('uid', String, primary_key=True)

    def __repr__(self):
        return "<User {}>".format(self.uid)


class OAuth2Token(db.Model):
    __tablename__ = 'oauth2tokens'
    __table_args__ = {'extend_existing': True}

    uid = Column('uid', ForeignKey('oc_users.uid'), primary_key=True)
    token_type = Column('token_type', String)
    access_token = Column('access_token', String)
    refresh_token = Column('refresh_token', String)
    expires_at = Column('expires_at', Integer)

    def to_dict(self):
        return dict(
            uid=self.uid,
            token_type=self.token_type,
            access_token=self.access_token,
            refresh_token=self.refresh_token,
            expires_at=self.expires_at
        )


class Datatype(db.Model):
    __tablename__ = 'datatypes'
    __table_args__ = {'extend_existing': True}

    datatype_id = Column('datatype_id', Integer, primary_key=True)
    datatype_name = Column('name', String)
    is_large = Column('is_large', Boolean)

    def to_dict(self):
        return dict(
            datatype_id=self.datatype_id,
            datatype_name=self.datatype_name,
            is_large=self.is_large
        )

    def __repr__(self):
        return "<Datatype ID {} - {}>".format(self.datatype_id, self.datatype_name)


class Device(db.Model):
    __tablename__ = 'devices'
    __table_args__ = {'extend_existing': True}

    device_id = Column('device_id', Integer, primary_key=True)
    device_name = Column('name', String)
    location = Column('location', String)
    uid = Column('uid', ForeignKey('oc_users.uid'))

    def to_dict(self):
        return dict(
            device_id=self.device_id,
            device_name=self.device_name,
            location=self.location,
            uid=self.uid
        )

    def __repr__(self):
        return "<Device {} - {}>".format(self.device_id, self.device_name)


class Sensor(db.Model):
    __tablename__ = 'sensors'
    __table_args__ = {'extend_existing': True}

    sensor_id = Column('sensor_id', Integer, primary_key=True)
    sensor_name = Column('name', String)
    topic = Column('topic', String)
    is_enabled = Column('is_enabled', Boolean)
    datatype_id = Column('datatype_id', ForeignKey('datatypes.datatype_id'))
    device_id = Column('device_id', ForeignKey('devices.device_id'))

    def __repr__(self):
        return "<Sensor {} - {}>".format(self.sensor_id, self.sensor_name)


tag_map = db.Table('oc_systemtag_object_mapping', db.Model.metadata,
    db.Column('objectid', db.Integer, db.ForeignKey('oc_filecache.fileid'), primary_key=True),
    db.Column('objecttype', db.String, default='files', primary_key=True),
    db.Column('systemtagid', db.Integer, db.ForeignKey('oc_systemtag.id'), primary_key=True),
    extend_existing=True
)


class File(db.Model):
    __tablename__ = 'oc_filecache'
    __table_args__ = {'extend_existing': True}

    file_id = Column('fileid', Integer, primary_key=True)
    path = Column('path', String)
    file_name = Column('name', String)
    mimetype = Column('mimetype', String)
    etag = Column('etag', String)

    tags = relationship(
        'Tag',
        secondary=tag_map, 
        lazy='subquery',
        backref=db.backref('files', lazy=True)
    )

    def __repr__(self):
        return "<File {} - {}>".format(self.file_id, self.file_name)


class Tag(db.Model):
    __tablename__ = 'oc_systemtag'
    __table_args__ = {'extend_existing': True}

    tag_id = Column('id', Integer, primary_key=True)
    tag_name = Column('name', String)

    def __repr__(self):
        return "<Tag {} - {}>".format(self.tag_id, self.tag_name)


class SensorFile(db.Model):
    __tablename__ = 'sensor_files'
    __table_args__ = {'extend_existing': True}
    
    file_id = Column('fileid', ForeignKey('oc_filecache.fileid'), primary_key=True)
    upload_date = Column('upload_date', DateTime)
    sensor_id = Column('sensor_id', ForeignKey('sensors.sensor_id'))

