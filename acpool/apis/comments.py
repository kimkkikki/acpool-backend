from acpool.models import db, Comments
from flask import Blueprint, request, session
from common.acpool_response import response
from common.decorator import login_required
import simplejson

comments_blueprint = Blueprint('comments_blueprint', __name__)


@comments_blueprint.route('/comments', methods=['POST'])
@login_required
def add_comments():
    username = session['username']
    body = simplejson.loads(request.data)
    if 'contents' not in body:
        return response(error_code=1000)

    contents = body['contents']

    if len(contents) == 0:
        return response()

    parent_id = None
    if 'parent_id' in body and body['parent_id'] != 0:
        parent_id = body['parent_id']

    comments = Comments()
    comments.username = username
    comments.contents = contents
    comments.parent_id = parent_id

    db.session.add(comments)
    db.session.commit()

    return response()


@comments_blueprint.route('/comments/<page>', methods=['GET'])
def get_comments(page):
    try:
        page = int(page)
    except ValueError:
        page = 1

    comments = Comments.query.filter(Comments.parent_id.is_(None)).order_by(Comments.created.desc()).paginate(page, 20, error_out=False)
    to_json = [item.to_json() for item in comments.items]

    return response({'comments': to_json, 'hasNext': comments.has_next})


@comments_blueprint.route('/comments/<comments_id>', methods=['DELETE'])
@login_required
def delete_comments(comments_id):
    username = session['username']
    comments = Comments.query.filter(Comments.id == comments_id).filter(Comments.username == username).first()

    if comments is None:
        return response(error_code=1000)

    db.session.delete(comments)
    db.session.commit()

    return response()
