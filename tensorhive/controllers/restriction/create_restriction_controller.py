from http import HTTPStatus
from tensorhive.models.Restriction import Restriction
from tensorhive.utils.DateUtils import DateUtils
from tensorhive.authorization import admin_required
from tensorhive.config import API
R = API.RESPONSES['restriction']
G = API.RESPONSES['general']


@admin_required
def create(restriction):
    try:
        new_restriction = Restriction(
            name=restriction.get('name'),
            starts_at=restriction['start'],
            is_global=restriction['isGlobal'],
            ends_at=DateUtils.try_parse_string(restriction.get('end'))
        )
        new_restriction.save()
    except AssertionError as e:
        content = {'msg': R['create']['failure']['invalid'].format(reason=e)}
        status = HTTPStatus.UNPROCESSABLE_ENTITY.value
    except Exception as e:
        content = {'msg': G['internal_error'] + str(e)}
        status = HTTPStatus.INTERNAL_SERVER_ERROR.value
    else:
        content = {
            'msg': R['create']['success'],
            'restriction': new_restriction.as_dict(include_groups=True, include_users=True, include_resources=True)
        }
        status = HTTPStatus.CREATED.value
    finally:
        return content, status
