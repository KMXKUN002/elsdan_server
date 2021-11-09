from datetime import date, datetime
import time
from json import dumps

import requests
from flask import request, Response
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restful import Resource
from requests.models import HTTPBasicAuth
from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
# webargs to extract and validate arguments in HTTP requests
from webargs import fields
from webargs.flaskparser import use_args

from app import app, db
from app.models import (Datatype, Device, File, Sensor,
                        SensorFile, Tag)

resp_msg = {
    'INSERT': "{} added successfully",
    'UPDATE': "{} updated successfully",
    'DELETE': "{} deleted successfully",
    'NO_PERMISSION': "No permissions over this object",
    'NO_ITEM': "No item satisfies your arguments"
}

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


def get_sensor_permission(sensor_id):
    (uid,) = db.session.query(Device.uid).join(Sensor)\
            .filter(Sensor.sensor_id == sensor_id).first()
    if uid != get_jwt_identity():
        return False
    return True


def file_namer(sensor_id, extension):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return "{}_sensor_{}.{}".format(now, sensor_id, extension)


def append_slash(dir):
    if dir[-1] == '/':
        return dir
    return dir + '/'


# def fetch_token(name):
#     uid = get_jwt_identity()
#     item = OAuth2Token.query.filter_by(
#         uid=uid
#     ).first()
#     if item:
#         return item.to_dict()


# def update_token(name, token):
#     uid = get_jwt_identity()
#     item = OAuth2Token.query.filter_by(
#         uid=uid
#     ).first()
#     if not item:
#         item = OAuth2Token(uid=uid)
#     item.token_type = token.get('token_type', 'bearer')
#     item.access_token = token.get('access_token')
#     item.refresh_token = token.get('refresh_token')
#     item.expires_at = token.get('expires_at')

#     db.session.add(item)
#     db.session.commit()
#     return item


class DatatypeResource(Resource):
    
    get_args = {
        'datatype_id': fields.Int(),
        'datatype_name': fields.Str(),
        'is_large': fields.Bool()
    }

    @use_args(get_args, location='json')
    @jwt_required()
    def get(self, get_args):
        statement = select(Datatype)
        # Filter by each parameter given in args
        # Equivalent to WHERE ... AND clauses
        for column_name in get_args:
            if 'name' in column_name:
                statement = statement.filter(
                    getattr(Datatype, column_name).contains(get_args[column_name])
                )
            else:
                statement = statement.filter(
                    getattr(Datatype, column_name) == get_args[column_name]
                )
        rows = db.session.execute(statement)

        if not rows:
            return {"msg": resp_msg['NO_ITEM']}, 404

        return [row.to_dict() for (row,) in rows]

    
    post_args = {
        'datatype_name': fields.Str(required=True),
        'is_large': fields.Bool(required=True)
    }

    @use_args(post_args, location='json')
    @jwt_required()
    def post(self, post_args):
        datatype = Datatype()
        
        for column_name in post_args:
            setattr(datatype, column_name, post_args[column_name])
        db.session.add(datatype)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['INSERT'].format(datatype)
        }, 201
        
    patch_args = {
        'datatype_id': fields.Int(required=True),
        'datatype_name': fields.Str(),
        'is_large': fields.Bool()
    }

    @use_args(patch_args, location='json')
    @jwt_required()
    def patch(self, patch_args):
        id = patch_args.pop('datatype_id')
        
        datatype = db.session.query(Datatype)\
            .filter(Datatype.datatype_id == id).first()
        if not datatype:
            return {"msg": resp_msg['NO_ITEM']}, 404

        for column_name in patch_args:
            setattr(datatype, column_name, patch_args[column_name])

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['UPDATE'].format(datatype)
        }, 200


class DeviceResource(Resource):
    get_args = {
        'device_id': fields.Int(),
        'device_name': fields.Str(),
        'location': fields.Str(),
        'uid': fields.Str()
    }

    @use_args(get_args, location='json')
    @jwt_required()
    def get(self, get_args):
        statement = select(Device)
        for column_name in get_args:
            if 'name' in column_name:
                statement = statement.filter(
                    getattr(Device, column_name).contains(get_args[column_name])
                )
            else:
                statement = statement.filter(
                    getattr(Device, column_name) == get_args[column_name]
                )
        rows = db.session.execute(statement).all()

        if not rows:
            return {"msg": resp_msg['NO_ITEM']}, 404

        return [row.to_dict() for (row,) in rows]
    

    post_args = {
        'device_name': fields.Str(required=True),
        'location': fields.Str(required=True)
    }

    @use_args(post_args, location='json')
    @jwt_required()
    def post(self, post_args):
        uid = get_jwt_identity()

        device = Device(uid=uid)
        
        for column_name in post_args:
            setattr(device, column_name, post_args[column_name])
        db.session.add(device)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['INSERT'].format(device)
        }, 201


    patch_args = {
        'device_id': fields.Int(required=True),
        'device_name': fields.Str(),
        'location': fields.Str()
    }

    @use_args(patch_args, location='json')
    @jwt_required()
    def patch(self, patch_args):
        id = patch_args.pop('device_id')
        
        device = db.session.query(Device)\
            .filter(Device.device_id == id).first()
        if not device:
            return {"msg": resp_msg['NO_ITEM']}, 404
        if device.uid != get_jwt_identity():
            return {"msg": resp_msg['NO_PERMISSION']}, 403

        for column_name in patch_args:
            setattr(device, column_name, patch_args[column_name])

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['UPDATE'].format(device)
        }, 200

    
    del_args ={
        'device_id': fields.Int(required=True)
    }

    @use_args(del_args, location='json')
    @jwt_required()
    def delete(self, del_args):
        id = del_args['device_id']
        
        device = db.session.query(Device)\
            .filter(Device.device_id == id).first()
        if not device:
            return {"msg":resp_msg['NO_ITEM']}, 404
        if device.uid != get_jwt_identity():
            return {"msg": resp_msg['NO_PERMISSION']}, 403
        
         # Delete all sensors attached to the device
        device_sensors = Sensor.query.filter(Sensor.device_id == id).all()
        for sensor in device_sensors:
            db.session.delete(sensor)

        try:
            db.session.commit()
            db.session.delete(device)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['DELETE'].format(device)
        }, 200


class SensorResource(Resource):
    get_args = {
        'sensor_id': fields.Int(),
        'sensor_name': fields.Str(),
        'topic': fields.Str(),
        'is_enabled': fields.Bool(),
        'datatype_id': fields.Int(),
        'device_id': fields.Int(),
        'location': fields.Str(),
        'datatype_name': fields.Str(),
        'is_large': fields.Bool(),
        'uid': fields.Str(),
        'device_name': fields.Str()
    }

    @use_args(get_args, location='json')
    @jwt_required()
    def get(self, get_args):
        statement = select(
            Sensor.sensor_id,
            Sensor.sensor_name,
            Sensor.topic,
            Sensor.is_enabled,
            Sensor.datatype_id,
            Sensor.device_id,
            Device.device_name,
            Device.uid,
            Device.location,
            Datatype.datatype_name,
            Datatype.is_large
        ).join(Datatype).join(Device)

        if 'datatype_name' in get_args:
            statement = statement.filter(
                Datatype.datatype_name.contains(
                    get_args.pop('datatype_name'))
            )
        if 'is_large' in get_args:
            statement = statement.filter(
                Datatype.is_large == get_args.pop('is_large'))
        if 'uid' in get_args:
            statement = statement.filter(
                Device.uid == get_args.pop('uid'))
        if 'device_name' in get_args:
            statement = statement.filter(
                Device.device_name.contains(get_args.pop('device_name')))
        if 'location' in get_args:
            statement = statement.filter(
                Device.location.contains(get_args.pop('location')))

        # Filter by each parameter given in args
        # Equivalent to WHERE ... AND clauses
        for column_name in get_args:
            if 'name' in column_name:
                statement = statement.filter(
                    getattr(Sensor, column_name).contains(get_args[column_name])
                )
            else:
                statement = statement.filter(
                    getattr(Sensor, column_name) == get_args[column_name])

        rows = db.session.execute(statement).all()

        if not rows:
            return {"msg": resp_msg['NO_ITEM']}, 404

        return [row._asdict() for row in rows]
    

    post_args = {
        'sensor_name': fields.Str(required=True),
        'topic': fields.Str(), 
        'is_enabled': fields.Boolean(missing=1),
        'datatype_id': fields.Int(required=True),
        'device_id': fields.Int(required=True)
    }

    @use_args(post_args, location='json')
    @jwt_required()
    def post(self, post_args):
        uid = get_jwt_identity()
        device = Device.query.filter_by(
            device_id=post_args['device_id']
        ).first()
        if not device or device.uid != uid:
            return {
                "msg": "Target device doesn't exist or you don't own it"
            }, 400

        sensor = Sensor()
        
        for column_name in post_args:
            setattr(sensor, column_name, post_args[column_name])
        db.session.add(sensor)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['INSERT'].format(sensor)
        }, 201


    patch_args = {
        'sensor_id': fields.Int(required=True),
        'sensor_name': fields.Str(),
        'topic': fields.Str(),
        'is_enabled': fields.Bool(),
        'datatype_id': fields.Int(),
        'device_id': fields.Int()
    }

    @use_args(patch_args, location='json')
    @jwt_required()
    def patch(self, patch_args):
        uid = get_jwt_identity()
        id = patch_args.pop('sensor_id')
        
        if 'device_id' in patch_args:
            device = Device.query.filter_by(
                device_id=patch_args['device_id']
            ).first()
            if not device or device.uid != uid:
                return {
                    "msg": "Target device doesn't exist or you don't own it"
                }, 400

        sensor = Sensor.query.filter_by(sensor_id=id).first()
        if not sensor:
            return{"msg": resp_msg['NO_ITEM']}, 404
        
        master_device = Device.query.filter_by(
            device_id=sensor.device_id).first()
        if master_device.uid != uid:
            return {"msg": resp_msg["NO_PERMISSION"]}, 403
        
        for column_name in patch_args:
            setattr(sensor, column_name, patch_args[column_name])

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['UPDATE'].format(sensor)
        }, 200

    
    del_args ={
        'sensor_id': fields.Int(required=True)
    }

    @use_args(del_args, location='json')
    @jwt_required()
    def delete(self, del_args):
        uid = get_jwt_identity()
        id = del_args['sensor_id']

        sensor = Sensor.query.filter_by(sensor_id=id).first()
        if not sensor:
            return {"msg": resp_msg['NO_ITEM']}, 404

        device = Device.query.filter_by(device_id=sensor.device_id).first()
        if device.uid != uid:
            return {"msg": resp_msg['NO_PERMISSION']}, 403

        db.session.delete(sensor)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['DELETE'].format(sensor)
        }, 200


class FileDetailResource(Resource):
    get_args = {
        'file_id': fields.Int(),
        'tag_id': fields.Int(),
        'tag_name': fields.Str(),
        'datatype_id': fields.Int(),
        'device_id': fields.Int(),
        'sensor_id': fields.Int(),
        'topic': fields.Str(),
        'start_date': fields.DateTime(format='%Y-%m-%dT%H:%M:%S'),
        'end_date': fields.DateTime(format='%Y-%m-%dT%H:%M:%S')
    }

    @use_args(get_args, location='json')
    @jwt_required()
    def get(self, get_args):
        statement = select(
            File.file_id,
            File.file_name,
            File.path,
            Sensor.sensor_id,
            Sensor.sensor_name,
            SensorFile.upload_date
        ).select_from(File).join(SensorFile).join(Sensor)\
            .filter(File.path.startswith('files/')).filter(File.mimetype > 2)
        
        if 'tag_id' in get_args or 'tag_name' in get_args:
            statement = statement.join(File.tags)
            if 'tag_id' in get_args:
                statement = statement.filter(Tag.tag_id == get_args['tag_id'])
            if 'tag_name' in get_args:
                statement = statement.filter(
                    Tag.tag_name.contains(get_args['tag_name']))
        if 'file_id' in get_args:
            statement = statement.filter(File.file_id == get_args['file_id'])
        if 'sensor_id' in get_args:
            statement = statement.filter(
                Sensor.sensor_id == get_args['sensor_id'])
        if 'start_date' in get_args:
            statement = statement.filter(
                SensorFile.upload_date > get_args['start_date'])
        if 'end_date' in get_args:
            statement = statement.filter(
                SensorFile.upload_date < get_args['end_date'])
        
        statement = statement.order_by(SensorFile.upload_date.desc())
        rows = db.session.execute(statement).all()

        if not rows:
            return {"msg": resp_msg['NO_ITEM']}, 404
        
        return Response(
            dumps([row._asdict() for row in rows], default=json_serial),
            mimetype='application/json'
        )


    put_args = {
        'file_id': fields.Int(required=True),
        'tag_id': fields.Int(),
        'sensor_id': fields.Int()
    }

    @use_args(put_args, location='json')
    @jwt_required()
    def put(self, put_args):
        # Find file
        file_id = put_args.pop('file_id')
        file = File.query.filter_by(file_id=file_id).first()

        if not file:
            return {"msg": resp_msg['NO_ITEM']}, 404

        # Confirm user has ownership over the File and Sensor
        sensorfile = SensorFile.query.filter_by(file_id=file_id).first()
        if not get_sensor_permission(sensorfile.sensor_id):
            return {"msg": resp_msg['NO_PERMISSION']}, 403

        if 'sensor_id' in put_args:
            sensor_id = put_args['sensor_id']
            if not get_sensor_permission(sensor_id):
                return {"msg": resp_msg['NO_PERMISSION']}, 403
            sensorfile.sensor_id = sensor_id
        if 'tag_id' in put_args:
            tag = Tag.query.filter_by(tag_id=put_args['tag_id']).first()
            if not tag:
                return {"msg": "No tag of that ID"}, 404
            file.tags.append(tag)
            db.session.add(file)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['UPDATE'].format(file)
        }, 200

    
    del_args = {
        'file_id': fields.Int(required=True),
        'tag_id': fields.Int(required=True)
    }

    @use_args(del_args, location='json')
    @jwt_required()
    def delete(self, del_args):
        # Find file
        file_id = del_args.pop('file_id')
        file = File.query.filter_by(file_id=file_id).first()

        if not file:
            return {"msg": resp_msg['NO_ITEM']}, 404
        
        # Confirm user has ownership over the File and Sensor
        sensorfile = SensorFile.query.filter_by(file_id=file_id).first()
        if not get_sensor_permission(sensorfile.sensor_id):
            return {"msg": resp_msg['NO_PERMISSION']}, 403

        tag = Tag.query.filter_by(tag_id=del_args['tag_id']).first()
        if tag not in file.tags:
            return {"msg": "File not tagged with that ID"}, 404
        file.tags.remove(tag)
        
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": "{} removed from {}".format(tag, file)
        }, 200


class TagResource(Resource):
    get_args = {
        'tag_id': fields.Int(),
        'tag_name': fields.Str()
    }

    @use_args(get_args, location='json')
    @jwt_required()
    def get(self, get_args):
        statement = select(
            Tag.tag_id,
            Tag.tag_name
        )

        if 'tag_id' in get_args:
            statement = statement.filter(
                Tag.tag_id == get_args['tag_id']
            )
        if 'tag_name' in get_args:
            statement = statement.filter(
                Tag.tag_name.contains(get_args['tag_name'])
            )
        
        rows = db.session.execute(statement).all()

        if not rows:
            return {"msg": resp_msg['NO_ITEM']}, 404

        return [row._asdict() for row in rows]

    post_args = {
        'tag_name': fields.Str(required=True)
    }

    @use_args(post_args, location='json')
    @jwt_required()
    def post(self, post_args):
        tag = Tag(tag_name=post_args['tag_name'])
        db.session.add(tag)

        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500
        
        return {
            "msg": resp_msg['INSERT'].format(tag)
        }, 200
    

class FileManageResource(Resource):
    put_args = {
        'sensor_id': fields.Int(required=True),
        'path': fields.Str(required=True),
        'tag_id': fields.Int(),
        'extension': fields.Str(required=True),
        'user': fields.Str(required=True),
        'password': fields.Str(required=True)
    }

    @use_args(put_args, location='headers')
    @jwt_required()
    def put(self, put_args):
        print("API receive time {}".format(round(time.time() * 1000)))
        uid = get_jwt_identity()
        user = put_args['user']
        password = put_args['password']

        sensor_id = put_args['sensor_id']
        path = put_args['path']
        extension = put_args['extension']

        if request.content_length == 0:
            return {"msg": "No file content"}

        if not Sensor.query.filter_by(sensor_id=sensor_id).first():
            return {"msg": resp_msg['NO_ITEM']}, 404

        if uid != user or not get_sensor_permission(sensor_id):
            return {"msg": resp_msg['NO_PERMISSION']}, 403
        
        if extension not in app.config['ALLOWED_EXTENSIONS']:
            return {"msg": "This extension is not allowed"}, 400

        path = append_slash(path) + file_namer(sensor_id, extension)
        endpoint = "{}{}{}".format(
            app.config['NEXTCLOUD_WEBDAV'],
            append_slash(uid),
            path)

        auth = HTTPBasicAuth(user, password)
        response = requests.put(
            endpoint,
            auth=auth,
            data=request.data,
        )
        response.raise_for_status()

        etag = response.headers.get('ETag').strip('"')
        file = File.query.filter_by(etag=etag).first()
        db.session.add(SensorFile(file_id=file.file_id, sensor_id=sensor_id))
        
        if 'tag_id' in put_args:
            tag = Tag.query.filter_by(tag_id=put_args['tag_id']).first()
            if not tag:
                return {"msg": "No tag of that ID"}, 404
            file.tags.append(tag)
            db.session.add(file)
        
        try:
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            return {
                "msg": str(e.__dict__['orig'])
            }, 500

        print("API respond time {}".format(round(time.time() * 1000)))
        return {
            "msg": "File uploaded successfully"
        }, response.status_code


