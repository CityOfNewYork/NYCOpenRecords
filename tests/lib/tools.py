import os
import random
import app.lib.file_utils as fu
from itertools import product
from datetime import datetime, timedelta
from flask import current_app
from string import (
    ascii_lowercase,
    digits,
)
from sqlalchemy.sql.expression import func
from app import calendar
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
    NOTE: Emails are not sent and no email Events are not created.
    """
    __files = []

    def __init__(self, request, clean=True):
        self.request = request
        self.__clean = clean

    def __getattr__(self, name):
        return getattr(self.request, name)

    def set_title(self, title: str):
        self.request.title = title

    def set_agency_description(self, agency_description: str):
        self.request.agency_description = agency_description

    def set_title_privacy(self, privacy: bool):
        self.request.privacy["title"] = privacy

    def set_agency_description_privacy(self, privacy: bool):
        self.request.privacy["agency_description"] = privacy

    def add_file(self,
                 title=None,
                 filepath=None,
                 name=None,
                 mime_type=None,
                 privacy=response_privacy.PRIVATE):
        if filepath is None:
            filename = name or fake.file_name(extension='txt')
            filepath = os.path.join(
                current_app.config["UPLOAD_DIRECTORY"],
                self.request.id,
                filename)
        else:
            filename = name or os.path.basename(filepath)

        if not fu.exists(filepath):
            fu.makedirs(os.path.dirname(filepath), exists_ok=True)
            with open(filepath, "w") as fp:
                fp.write(fake.file_content())

        self.__files.append(filepath)

        response = Files(
            self.request.id,
            privacy=privacy,
            title=title or fake.title(),
            name=filename,
            mime_type=mime_type or fu.get_mime_type(filepath),
            size=fu.getsize(filepath),
            hash_=fu.get_hash(filepath),
        )
        create_response_event(event_type.FILE_ADDED, response)
        create_object(response)
        return response

    def add_link(self, title=None, url=None, privacy=response_privacy.PRIVATE):
        response = Links(
            self.request.id,
            privacy,
            title=title or fake.title(),
            url=url or fake.url()
        )
        create_response_event(event_type.LINK_ADDED, response)
        create_object(response)
        return response

    def add_note(self, content=None, privacy=response_privacy.PRIVATE):
        response = Notes(
            self.request.id,
            privacy,
            content=content or fake.paragraph()
        )
        create_response_event(event_type.NOTE_ADDED, response)
        create_object(response)
        return response

    def add_instructions(self, content=None, privacy=response_privacy.PRIVATE):
        response = Instructions(
            self.request.id,
            privacy,
            content=content or fake.paragraph()
        )
        create_response_event(event_type.INSTRUCTIONS_ADDED, response)
        create_object(response)
        return response

    def acknowledge(self, info=None, days=None, date=None):
        if date is not None and info is not None:
            info = fake.paragraph()
        new_due_date = self.__get_new_due_date(days, date)
        return self.__extend(
            determination_type.ACKNOWLEDGMENT,
            new_due_date,
            {
                "due_date": new_due_date,
                "status": request_status.IN_PROGRESS
            },
            info
        )

    def extend(self, reason=None, days=None, date=None):
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
            {"status": new_status},
            reason or fake.paragraph()
        )

    def reopen(self, date):
        return self.__extend(
            determination_type.REOPENING,
            process_due_date(local_to_utc(date, current_app.config["TIMEZONE_NAME"])),
            {
                "status": request_status.IN_PROGRESS,
                "agency_description_release_date": None
            }
        )

    def __extend(self, extend_type, new_due_date, request_update_data=None, reason=None):
        request_update_data["due_date"] = new_due_date
        update_object(
            request_update_data,
            Requests,
            self.request.id
        )
        response = Determinations(
            self.request.id,
            response_privacy.RELEASE_AND_PUBLIC,
            extend_type,
            reason,
            new_due_date
        )
        create_object(response)
        create_response_event(extend_type, response)
        return response

    def __get_new_due_date(self, days=None, date=None):
        assert days is not None or date is not None
        tz_name = current_app.config["TIMEZONE_NAME"]
        if days is None:
            date = datetime.strptime(date, '%Y-%m-%d')
            new_due_date = process_due_date(local_to_utc(date, tz_name))
        else:
            new_due_date = get_due_date(
                utc_to_local(
                    self.request.due_date,
                    tz_name
                ),
                int(days),
                tz_name)
        return new_due_date

    def deny(self, reason_ids=None):
        return self.__close(determination_type.DENIAL, reason_ids)

    def close(self, reason_ids=None):
        return self.__close(determination_type.CLOSING, reason_ids)

    def __close(self, close_type, reason_ids=None):
        if reason_ids is None:
            reasons = "|".join(
                (r.content for r in
                 Reasons.query.filter_by(
                     type=close_type
                 ).order_by(
                     func.random()
                 ).limit(
                     random.randrange(5)
                 ).all()))
        else:
            reasons = format_determination_reasons(reason_ids)
        update_object(
            {
                "status": request_status.CLOSED,
                "agency_descripton_release_date": calendar.addbusdays(
                    datetime.utcnow(), RELEASE_PUBLIC_DAYS)
            },
            Requests,
            self.request.id
        )
        response = Determinations(
            self.request.id,
            response_privacy.RELEASE_AND_PUBLIC,
            close_type,
            reasons,
        )
        create_object(response)
        create_response_event(event_type.REQ_CLOSED, response)
        return response

    def set_due_soon(self, date=None):  # TODO
        # assert date >  date <  # DUE_SOON_DAYS
        pass

    def set_overdue(self, date=None):  # TODO
        assert date > datetime.utcnow()

    def add_user(self, user, permissions=None, role=None):
        """
        Assign user to request.
        A role name or permissions must be supplied if the supplied user is not anonymous nor public
        (i.e. is an agency user) as there are multiple roles to choose from for agency users.
        """
        if role is None and permissions is None:
            assert user.auth_user_type in (user_type_auth.ANONYMOUS_USER, user_type_auth.PUBLIC_USER_TYPES)
            role = {
                user_type_auth.ANONYMOUS_USER: role_name.ANONYMOUS,
                user_type_auth.PUBLIC_USER_TYPES: role_name.PUBLIC_REQUESTER
            }[user.auth_user_type]
        permissions = permissions or Roles.query.filter_by(name=role).one().permissions
        user_request = UserRequests(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=self.request.id,
            request_user_type=user_type_request.AGENCY if user.is_agency else user_type_request.REQUESTER,
            permissions=permissions
        )
        create_object(user_request)
        create_user_request_event(event_type.USER_ADDED, user_request)
        return user_request

    def edit_user(self, user, perms_set=None, perms_add=None, perms_remove=None):
        """
        Edit assigned user permissions.
        At least one permission-specific argument must be passed.
        """
        assert perms_set or perms_add or perms_remove
        user_request = UserRequests.filter_by(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=self.request.id
        ).one().id
        old_permissions = user_request.permissions
        if perms_set:
            user_request.set_permissions(perms_set)
        if perms_add:
            user_request.add_permissions(perms_add)
        if perms_remove:
            user_request.remove_permissions(perms_remove)
        create_user_request_event(event_type.USER_PERM_CHANGED, user_request, old_permissions)

    def remove_user(self, user):
        """ Un-assign user. """
        user_request = UserRequests.filter_by(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=self.request.id
        ).one()
        create_user_request_event(event_type.USER_REMOVED, user_request)
        delete_object(user_request)

    def __del__(self):
        """
        Remove any *non-database* artifacts created for this request.
        """
        if self.__clean:
            for path in self.__files:
                if fu.exists(path):
                    fu.remove(path)


class RequestsFactory(object):
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
                       agency_description=None,
                       agency_ein=None,
                       date_created=None,
                       date_submitted=None,
                       due_date=None,
                       category=None,
                       privacy=None,
                       submission=None,
                       status=request_status.OPEN):
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
            assert agency_ein or self.agency_ein  == user.agency_ein, \
                "user's agency ein must match supplied agency ein"
        agency_ein = agency_ein or self.agency_ein or user.agency_ein or get_random_agency().ein

        # create dates
        tz_name = current_app.config["TIMEZONE_NAME"]
        date_created_local = utc_to_local(datetime.utcnow(), tz_name)
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
            privacy=privacy,
            submission=submission or random.choice(submission_methods.ALL),
            status=status,
        )
        if agency_description is not None:
            request.agency_description = agency_description
        request = RequestWrapper(request)

        # create events
        timestamp = datetime.utcnow()
        create_object(Events(
            user_guid=user.guid,
            auth_user_type=user.auth_user_type,
            request_id=request.id,
            type_=event_type.REQ_CREATED,
            timestamp=timedelta,
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

        # add users TODO: assign other agency users
        request.add_user(user)
        if user.is_agency:
            request.add_user(self.__uf.create_anonymous_user())

        return request

    def create_request_as_anonymous_user(self, **kwargs):
        return self.create_request(self.__uf.create_anonymous_user(), **kwargs)

    def create_request_as_agency_user(self, **kwargs):
        return self.create_request(self.agency_user, **kwargs)

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
                    email_validated=False,
                    terms_of_use_accepted=False):
        if auth_type == user_type_auth.AGENCY_USER:
            assert agency_ein is not None
        user = Users(
            guid=guid or self.generate_user_guid(auth_type),
            auth_user_type=auth_type,
            agency_ein=agency_ein,
            email=email or fake.email(),
            first_name=first_name or fake.first_name(),
            last_name=last_name or fake.last_name(),
            title=title or fake.title(),
            organization=organization or fake.organization(),
            phone_number=phone_number or fake.phone_number(),
            fax_number=fax_number or fake.fax_number(),
            mailing_address=mailing_address or fake.mailing_address(),
            email_validated=email_validated,
            terms_of_use_accepted=terms_of_use_accepted)
        create_object(user)
        return user

    def create_anonymous_user(self):
        return self.create_user(user_type_auth.ANONYMOUS_USER)

    def create_agency_user(self, agency_ein=None):
        return self.create_user(
            user_type_auth.AGENCY_USER,
            agency_ein=agency_ein or get_random_agency().ein)

    def create_public_user(self):
        return self.create_user(random.choice(user_type_auth.PUBLIC_USER_TYPES))

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

    for title_private, agency_desc_private, is_requester in product(range(2), repeat=3):
        for title, description, agency_description in product(("foo", "bar", "qux"), repeat=3):
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
                                      ACKNOWLEDGMENT_DAYS_DUE),
                submission=submission_methods.DIRECT_INPUT,
                status=random.choice((request_status.OPEN,
                                      request_status.CLOSED,
                                      request_status.OVERDUE,
                                      request_status.IN_PROGRESS,
                                      request_status.DUE_SOON)),
                privacy={
                    'title': bool(title_private),
                    'agency_description': bool(agency_desc_private)
                }
            )
            request.agency_description = agency_description
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
