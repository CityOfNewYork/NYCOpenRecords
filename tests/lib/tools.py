import os
import random
import app.lib.file_utils as fu
from itertools import product
from contextlib import contextmanager
from datetime import datetime, timedelta
from flask import current_app
from string import (
    ascii_lowercase,
    digits,
)
from flask_login import login_user, logout_user
from sqlalchemy.sql.expression import func
from app import calendar, db
from app.models import (
    Requests,
    Reasons,
    Events,
    Determinations,
    Files,
    Links,
    Notes,
    Instructions,
    Users,
    Agencies,
    UserRequests,
    Roles,
    Responses,
)
from app.constants import (
    ACKNOWLEDGMENT_DAYS_DUE,
    determination_type,
    submission_methods,
    user_type_request,
    response_privacy,
    user_type_auth,
    request_status,
    event_type,
    role_name,
)
from app.constants.request_date import RELEASE_PUBLIC_DAYS
from app.lib.db_utils import (
    create_object,
    update_object,
    delete_object,
)
from app.lib.date_utils import (
    get_following_date,
    process_due_date,
    get_due_date,
    utc_to_local,
    local_to_utc,
)
from app.request.utils import (
    generate_guid as generate_guid_anon,
    generate_request_id,
)
from app.response.utils import (
    format_determination_reasons,
    create_response_event,
)
from app.user_request.utils import create_user_request_event
from tests.lib.faker_providers import fake
from tests.lib.constants import NON_ANON_USER_GUID_LEN


class RequestWrapper(object):
    """
    Wrapper class for request objects; provides convenience methods.

    NOTE:
    - While you will be able to access Requests object attributes directly
     (e.g. RequestWrapper(Request(...)).id ), dev tools will only provide a suggestion list
     for methods in this class; should you desire suggestions for the wrapped request
     you will have to reference it explicitly (e.g. RequestsWrapper(Request(...)).request.id).
    - Emails are not sent and no email Events are created.
    """
    __files = []
    __tz_name = current_app.config["APP_TIMEZONE"]

    def __init__(self, request, user=None, clean=True):
        """
        :param request: the request to wrap
        :param user: primary user for actions performed
            if not supplied, will try to fetch assigned user
        :param clean: remove artifacts on object deletion?
        """
        self.request = request
        self.user = user or request.agency_users.first()
        self.__clean = clean

    def __getattr__(self, name):
        return getattr(self.request, name)

    def set_title(self, title: str):
        self.__update({"title": title})

    def set_agency_request_summary(self, agency_request_summary: str):
        self.__update({"agency_request_summary": agency_request_summary})

    def set_title_privacy(self, privacy: bool):
        self.__update({"privacy": {"title": privacy}})

    def set_agency_request_summary_privacy(self, privacy: bool):
        release_date = calendar.addbusdays(datetime.utcnow(), RELEASE_PUBLIC_DAYS) if not privacy else None
        self.__update({"privacy": {"agency_request_summary": privacy},
                       "agency_request_summary_release_date": release_date})

    def add_file(self,
                 title=None,
                 filepath=None,
                 name=None,  # will be ignored if filepath supplied
                 privacy=response_privacy.PRIVATE,
                 user=None):
        if filepath is None:
            filename = name or fake.file_name(extension='txt')
            filepath = os.path.join(
                current_app.config["UPLOAD_DIRECTORY"],
                self.request.id,
                filename)
        else:
            filename = os.path.basename(filepath)

        if not fu.exists(filepath):
            fu.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as fp:
                fp.write(fake.file_content())
            self.__files.append(filepath)

        response = Files(
            self.request.id,
            privacy=privacy,
            title=title or fake.title(),
            name=filename,
            mime_type=fu.get_mime_type(filepath),
            size=fu.getsize(filepath),
            hash_=fu.get_hash(filepath),
        )
        create_object(response)
        self.__create_event(event_type.FILE_ADDED, response, user)
        return response

    def add_link(self, title=None, url=None, privacy=response_privacy.PRIVATE, user=None):
        response = Links(
            self.request.id,
            privacy,
            title=title or fake.title(),
            url=url or fake.url()
        )
        create_object(response)
        self.__create_event(event_type.LINK_ADDED, response, user)
        return response

    def add_note(self, content=None, privacy=response_privacy.PRIVATE, user=None):
        response = Notes(
            self.request.id,
            privacy,
            content=content or fake.paragraph()
        )
        create_object(response)
        self.__create_event(event_type.NOTE_ADDED, response, user)
        return response

    def add_instructions(self, content=None, privacy=response_privacy.PRIVATE, user=None):
        response = Instructions(
            self.request.id,
            privacy,
            content=content or fake.paragraph()
        )
        create_object(response)
        self.__create_event(event_type.INSTRUCTIONS_ADDED, response, user)
        return response

    def acknowledge(self, info=None, days=None, date=None, user=None):
        if date is not None and info is None:
            # info required if custom date used
            info = fake.paragraph()
        new_due_date = self.__get_new_due_date(days, date)
        return self.__extend(
            determination_type.ACKNOWLEDGMENT,
            new_due_date,
            user,
            {"status": request_status.IN_PROGRESS},
            info
        )

    def extend(self, reason=None, days=None, date=None, user=None):
        new_due_date = self.__get_new_due_date(days, date)
        days_until_due = calendar.busdaycount(
            datetime.utcnow(), new_due_date.replace(hour=23, minute=59, second=59))
        if new_due_date < datetime.utcnow():
            new_status = request_status.OVERDUE
        elif days_until_due <= current_app.config['DUE_SOON_DAYS_THRESHOLD']:
            new_status = request_status.DUE_SOON
        else:
            new_status = request_status.IN_PROGRESS
        return self.__extend(
            determination_type.EXTENSION,
            new_due_date,
            user,
            {"status": new_status},
            reason or fake.paragraph()
        )

    def reopen(self, date, user=None):
        return self.__extend(
            determination_type.REOPENING,
            process_due_date(local_to_utc(date, self.__tz_name)),
            user,
            {
                "status": request_status.IN_PROGRESS,
                "agency_request_summary_release_date": None
            }
        )

    def __extend(self, extend_type, new_due_date, user, request_update_data=None, reason=None):
        assert new_due_date > self.request.due_date
        request_update_data["due_date"] = new_due_date
        self.__update(request_update_data)
        response = Determinations(
            self.request.id,
            response_privacy.RELEASE_AND_PUBLIC,
            extend_type,
            reason,
            new_due_date
        )
        create_object(response)
        self.__create_event(extend_type, response, user)
        return response

    def __get_new_due_date(self, days=None, date=None):
        assert days is not None or date is not None
        if days is None:
            new_due_date = process_due_date(local_to_utc(date, self.__tz_name))
        else:
            new_due_date = get_due_date(
                utc_to_local(
                    self.request.due_date,
                    self.__tz_name
                ),
                days,
                self.__tz_name)
        return new_due_date

    def deny(self, reason_ids=None, user=None):
        return self.__close(determination_type.DENIAL, user, reason_ids)

    def close(self, reason_ids=None, user=None):
        return self.__close(determination_type.CLOSING, user, reason_ids)

    def __close(self, close_type, user, reason_ids=None):
        if reason_ids is None:
            reasons = "|".join(
                (r.content for r in
                 Reasons.query.filter_by(
                     type=close_type
                 ).order_by(
                     func.random()
                 ).limit(
                     random.randrange(1, 6)
                 ).all()))
        else:
            reasons = format_determination_reasons(reason_ids)
        self.__update(
            {
                "status": request_status.CLOSED,
                "agency_request_summary_release_date": calendar.addbusdays(
                    datetime.utcnow(), RELEASE_PUBLIC_DAYS)
            }
        )
        response = Determinations(
            self.request.id,
            response_privacy.RELEASE_AND_PUBLIC,
            close_type,
            reasons,
        )
        create_object(response)
        self.__create_event(event_type.REQ_CLOSED, response, user)
        return response

    def set_due_soon(self, days=current_app.config["DUE_SOON_DAYS_THRESHOLD"], shift_dates=True):
        """
        Shift request date field values, with due date set to up to 2 days
        (DUE_SOON_DAYS_THRESHOLD) from now, and sets request statues to "due_soon".

        :param days: days until request is due (max: 2)
        :param shift_dates: shift dates or only change status?
        """
        days = min(days, current_app.config["DUE_SOON_DAYS_THRESHOLD"])
        self.__set_due_soon_or_overdue(
            request_status.DUE_SOON,
            calendar.addbusdays(
                datetime.utcnow(), days
            ).replace(hour=23, minute=59, second=59, microsecond=0),
            shift_dates
        )

    def set_overdue(self, shift_dates=True):
        """
        Shift request date field values, with due date set to yesterday,
        and sets request statues to "overdue".

        :param shift_dates: shift dates or only change status?
        """
        self.__set_due_soon_or_overdue(
            request_status.OVERDUE,
            calendar.addbusdays(
                datetime.utcnow(), -1
            ).replace(microsecond=0),
            shift_dates
        )

    def __set_due_soon_or_overdue(self, status, new_due_date, shift_dates):
        data = {"status": status}
        if shift_dates:
            shift = new_due_date - self.request.due_date
            data.update({
                "due_date": new_due_date,
                "date_submitted": self.request.date_submitted + shift,
                "date_created": self.request.date_created + shift,
                "agency_request_summary_release_date": (
                    self.request.agency_request_summary_release_date + shift
                    if self.request.agency_request_summary_release_date
                    else None
                )
            })
        create_object(
            Events(
                self.request.id,
                user_guid=None,
                auth_user_type=None,
                type_=event_type.REQ_STATUS_CHANGED,
                previous_value={"status": self.request.status},
                new_value={"status": status},
                response_id=None
            )
        )
        self.__update(data)

    def __update(self, data):
        update_object(data, Requests, self.request.id)

    def add_user(self, user, permissions=None, role=None, agent=None):
        """
        Assign user to request.
        If a role is not supplied, one will be provided and permissions
        will be set based on the user's status:
            anonymous           role_name.ANONYMOUS
            public              role_name.PUBLIC_REQUESTER
            agency admin        role_name.AGENCY_ADMIN
            agency user         role_name.AGENCY_OFFICER
            agency inactive     role_name.AGENCY_HELPER

        :param user: user to add
        :param permissions: permissions to grant to user
        :param role: role from which to retrieve permissions to grant to user
        :param agent: user performing this action
        :return: created UserRequests object
        """
        if role is None and permissions is None:
            if user.auth_user_type == user_type_auth.ANONYMOUS_USER:
                role = role_name.ANONYMOUS
            elif user.auth_user_type in user_type_auth.PUBLIC_USER_TYPES:
                role = role_name.PUBLIC_REQUESTER
            elif user.auth_user_type == user_type_auth.AGENCY_USER:
                if user.is_agency_active:
                    role = role_name.AGENCY_ADMIN if user.is_agency_admin else role_name.AGENCY_OFFICER
                else:
                    role = role_name.AGENCY_HELPER
        permissions = permissions or Roles.query.filter_by(name=role).one().permissions
        user_request = UserRequests(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=self.request.id,
            request_user_type=user_type_request.AGENCY if user.is_agency else user_type_request.REQUESTER,
            permissions=permissions
        )
        create_object(user_request)
        self.__create_event(event_type.USER_ADDED, user_request, agent)
        return user_request

    def edit_user(self, user, perms_set=None, perms_add=None, perms_remove=None, agent=None):
        """
        Edit assigned user permissions for request.
        At least one permission-specific argument must be passed.
        :param user: user to edit
        :param perms_set: permissions to set
        :param perms_add: permissions to add
        :param perms_remove: permissions to remove
        :param agent: user performing this action
        """
        assert perms_set is not None or perms_add is not None or perms_remove is not None
        user_request = UserRequests.query.filter_by(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=self.request.id
        ).one()
        old_permissions = user_request.permissions
        if perms_set:
            user_request.set_permissions(perms_set)
        if perms_add:
            user_request.add_permissions(perms_add)
        if perms_remove:
            user_request.remove_permissions(perms_remove)
        self.__create_event(event_type.USER_PERM_CHANGED, user_request, agent,
                            old_permissions=old_permissions)

    def remove_user(self, user, agent=None):
        """
        Un-assign user from request.
        :param user: user to remove
        :param agent: user performing this action
        """
        user_request = UserRequests.query.filter_by(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=self.request.id
        ).one()
        self.__create_event(event_type.USER_REMOVED, user_request, agent)
        delete_object(user_request)

    def __create_event(self, type_, obj, user=None, **kwargs):
        """
        Create a Responses or UserRequests event.
        :param type_: event type
        :param obj: Responses or UserRequests object
        :param user: user creating event
        """
        assert (isinstance(obj, Responses) or isinstance(obj, UserRequests))
        assert (user or self.user), "a user must be provided when creating a Responses or UserRequests event"
        user = user or self.user
        if isinstance(obj, Responses):
            create_response_event(type_, obj, user)
        elif isinstance(obj, UserRequests):
            create_user_request_event(type_, obj, user=user, **kwargs)

    def __del__(self):
        """
        Remove any *non-database* artifacts created for this request.
        """
        if self.__clean:
            for path in self.__files:
                if fu.exists(path):
                    fu.remove(path)


class RequestFactory(object):
    """
    Class for generating requests.
    """

    def __init__(self, agency_ein=None):
        """
        If an agency ein is supplied, it will serve as a
        fallback for all requests generated by this factory.
        """
        self.agency_ein = agency_ein
        self.__uf = UserFactory()
        self.agency_user = self.__uf.create_agency_user(agency_ein)
        self.public_user = self.__uf.create_public_user()

    def create_request(self,
                       user,
                       title=None,
                       description=None,
                       agency_request_summary=None,  # TODO: agency_request_summary_release_date
                       agency_ein=None,
                       date_created=None,
                       date_submitted=None,
                       due_date=None,
                       category=None,
                       title_privacy=True,
                       agency_request_summary_privacy=True,
                       submission=None,
                       status=request_status.OPEN,
                       tz_name=current_app.config["APP_TIMEZONE"]):
        """
        Create a request as the supplied user. An anonymous requester
        will be created if the supplied user is an agency user.
        :rtype: RequestWrapper
        """
        # check due date
        if (date_created is not None or date_submitted is not None) and due_date is not None:
            def assert_date(date, date_var_str):
                assert (due_date - date).days >= 1, "due_date must be at least 1 day after " + date_var_str

            if date_created is not None:
                assert_date(date_created, "date_created")
            if date_submitted is not None:
                assert_date(date_submitted, "date_submitted")

        # check agency_ein
        if (agency_ein is not None or self.agency_ein is not None) \
                and user.auth_user_type == user_type_auth.AGENCY_USER:
            assert (agency_ein or self.agency_ein) == user.agency_ein, \
                "user's agency ein must match supplied agency ein"
        agency_ein = agency_ein or self.agency_ein or user.agency_ein or get_random_agency().ein

        # create dates
        date_created_local = utc_to_local(date_created or datetime.utcnow(), tz_name)
        date_submitted_local = date_submitted or get_following_date(date_created_local)
        due_date = due_date or get_due_date(date_submitted_local, ACKNOWLEDGMENT_DAYS_DUE, tz_name)
        date_created = date_created or local_to_utc(date_created_local, tz_name)
        date_submitted = date_submitted or local_to_utc(date_submitted_local, tz_name)

        # create request
        request = Requests(
            generate_request_id(agency_ein),
            title or fake.title(),
            description or fake.description(),
            agency_ein=agency_ein,
            date_created=date_created or datetime.utcnow(),
            date_submitted=date_submitted,
            due_date=due_date,
            category=category,
            privacy={"title": title_privacy, "agency_request_summary": agency_request_summary_privacy},
            submission=submission or random.choice(submission_methods.ALL),
            status=status,
        )
        if agency_request_summary is not None:
            request.agency_request_summary = agency_request_summary
        if agency_request_summary_privacy is not None:
            request.agency_request_summary_release_date = calendar.addbusdays(
                datetime.utcnow(), RELEASE_PUBLIC_DAYS) if not agency_request_summary_privacy else None
        create_object(request)
        request = RequestWrapper(request, self.agency_user)

        # create events
        timestamp = datetime.utcnow()
        create_object(Events(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=request.id,
            type_=event_type.REQ_CREATED,
            timestamp=timestamp,
            new_value=request.val_for_events
        ))
        if user.is_agency:
            create_object(Events(
                user_guid=user.guid,
                auth_user_type=user.auth_user_type,
                request_id=request.id,
                type_=event_type.AGENCY_REQ_CREATED,
                timestamp=timestamp
            ))

        # add users
        if user.is_public or user.is_anonymous_requester:
            request.add_user(user)
        if user.is_agency:  # then create and add anonymous requester
            request.add_user(self.__uf.create_anonymous_user())
        for admin in Agencies.query.filter_by(ein=agency_ein).one().administrators:
            request.add_user(admin)

        # create request doc now that requester is set
        request.es_create()

        return request

    def create_request_as_anonymous_user(self, **kwargs):
        return self.create_request(self.__uf.create_anonymous_user(), **kwargs)

    def create_request_as_agency_user(self, **kwargs):
        return self.create_request(
            self.agency_user, agency_ein=self.agency_user.agency_ein, **kwargs)

    def create_request_as_public_user(self, **kwargs):
        return self.create_request(self.public_user, **kwargs)


class UserFactory(object):
    """
    Class for generating users.
    """

    def create_user(self,
                    auth_type,
                    guid=None,
                    agency_ein=None,
                    email=None,
                    first_name=None,
                    last_name=None,
                    title=None,
                    organization=None,
                    phone_number=None,
                    fax_number=None,
                    mailing_address=None,
                    email_validated=True,
                    terms_of_use_accepted=True,
                    is_agency_active=False,
                    is_agency_admin=False):
        if auth_type == user_type_auth.AGENCY_USER:
            assert agency_ein is not None
        else:
            assert all((agency_ein is None, not is_agency_active, not is_agency_admin))
        if auth_type == user_type_auth.ANONYMOUS_USER:
            email_validated, terms_of_use_accepted = False, False
        user = Users(
            guid=guid or self.generate_user_guid(auth_type),
            auth_user_type=auth_type,
            agency_ein=agency_ein,
            email=email or fake.email(),
            first_name=first_name or fake.first_name(),
            last_name=last_name or fake.last_name(),
            title=title or fake.user_title(),
            organization=organization or fake.organization(),
            phone_number=phone_number or fake.phone_number(),
            fax_number=fax_number or fake.fax_number(),
            mailing_address=mailing_address or fake.mailing_address(),
            email_validated=email_validated,
            terms_of_use_accepted=terms_of_use_accepted,
            is_agency_active=is_agency_active,
            is_agency_admin=is_agency_admin,
        )
        create_object(user)
        return user

    def create_anonymous_user(self, **kwargs):
        return self.create_user(user_type_auth.ANONYMOUS_USER, **kwargs)

    def create_agency_user(self, agency_ein=None, **kwargs):
        return self.create_user(
            user_type_auth.AGENCY_USER,
            agency_ein=agency_ein or get_random_agency().ein,
            **kwargs)

    def create_agency_admin(self, agency_ein=None, **kwargs):
        return self.create_agency_user(agency_ein, is_agency_active=True, is_agency_admin=True, **kwargs)

    def create_public_user(self, **kwargs):
        return self.create_user(random.choice(list(user_type_auth.PUBLIC_USER_TYPES)), **kwargs)

    @staticmethod
    def generate_user_guid(auth_type):
        if auth_type == user_type_auth.ANONYMOUS_USER:
            return generate_guid_anon()
        else:
            return ''.join(random.choice(ascii_lowercase + digits)
                           for _ in range(NON_ANON_USER_GUID_LEN))


def get_random_agency():
    return Agencies.query.order_by(func.random()).limit(1).one()


def create_requests_search_set(requester, other_requester):
    """
    Generate 216 unique requests.
    Every combination of title content, description content, agency description content,
    title privacy, agency description privacy, and requester is guaranteed to be unique.
    """
    agency_eins = [ein[0] for ein in
                   Agencies.query.with_entities(Agencies.ein).all()]

    for title_private, agency_request_summary_private, is_requester in product(range(2), repeat=3):
        for title, description, agency_request_summary in product(("foo", "bar", "qux"), repeat=3):
            agency_ein = random.choice(agency_eins)
            date_created = get_random_date(datetime(2015, 1, 1), datetime(2016, 1, 1))
            date_submitted = get_following_date(date_created)
            # TODO: use rf = RequestsFactory()
            request = Requests(
                generate_request_id(agency_ein),
                title=title,
                description=description,
                agency_ein=agency_ein,
                date_created=date_created,
                date_submitted=date_submitted,
                due_date=get_due_date(date_submitted,
                                      ACKNOWLEDGMENT_DAYS_DUE,
                                      'US/Eastern'),
                submission=submission_methods.DIRECT_INPUT,
                status=random.choice((request_status.OPEN,
                                      request_status.CLOSED,
                                      request_status.OVERDUE,
                                      request_status.IN_PROGRESS,
                                      request_status.DUE_SOON)),
                privacy={
                    'title': bool(title_private),
                    'agency_request_summary': bool(agency_request_summary_private)
                }
            )
            request.agency_request_summary = agency_request_summary
            create_object(request)
            user_request = UserRequests(
                user_guid=(requester.guid if is_requester
                           else other_requester.guid),
                auth_user_type=(requester.auth_user_type if is_requester
                                else other_requester.auth_user_type),
                request_id=request.id,
                request_user_type=user_type_request.REQUESTER,
                permissions=11
            )
            create_object(user_request)


def get_random_date(start, end):
    """
    :type start: datetime
    :type end: datetime
    """
    return start + timedelta(
        seconds=random.randint(
            0, int((end - start).total_seconds())
        ))


def login_user_with_client(client, user_id):
    with client.session_transaction() as session:
        session['user_id'] = user_id
        session['fresh'] = True


@contextmanager
def flask_login_user(user):
    login_user(user)
    yield
    logout_user()


class TestHelpers(object):
    """
    Mixin class for unittests.
    """

    def assert_flashes(self, expected_message, expected_category):
        """
        Assert flash messages are flashed properly with expected message and category.
        :param expected_message: expected flash message
        :param expected_category: expected flash category
        """
        with self.client.session_transaction() as session:
            try:
                category, message = session['_flashes'][0]
            except KeyError:
                raise AssertionError('Nothing was flashed')
            assert expected_message in message
            assert expected_category == category

    def assert_response_event(self, request_id, type_, response, user):
        """
        Assert event created is properly committed with correct fields.

        :param request_id: FOIL request ID
        :param type_: type of event
        :param response: response object
        :param user: user object
        """
        event = Events.query.filter_by(response_id=response.id).one()
        self.assertEqual(
            [
                event.user_guid,
                event.auth_user_type,
                event.request_id,
                event.type,
                event.previous_value,
                event.new_value
            ],
            [
                user.guid,
                user.auth_user_type,
                request_id,
                type_,
                None,
                response.val_for_events,
            ]
        )
