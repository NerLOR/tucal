# https://events.htu.at/

from typing import List, Dict, Any
import json
import datetime

import tucal
import tucal.db
import tuwien.sso

QUERY = {
    'operationName': 'SearchEventsAndGroups',
    'variables': {
        'eventPage': 1,
        'limit': 10000,
        'beginsOn': None,
        'endsOn': None,
    },
    'query': """
        query SearchEventsAndGroups($location: String, $radius: Float, $tags: String, $term: String, $type: EventType, $beginsOn: DateTime, $endsOn: DateTime, $eventPage: Int, $limit: Int) {
          searchEvents(
            location: $location
            radius: $radius
            tags: $tags
            term: $term
            type: $type
            beginsOn: $beginsOn
            endsOn: $endsOn
            page: $eventPage
            limit: $limit
          ) {
            total
            elements {
              id
              uuid
              url
              local
              title
              description
              beginsOn
              endsOn
              status
              visibility
              insertedAt
              language
              picture {
                id
                url
                __typename
              }
              publishAt
              physicalAddress {
                ...AdressFragment
                __typename
              }
              organizerActor {
                ...ActorFragment
                __typename
              }
              attributedTo {
                ...ActorFragment
                __typename
              }
              category
              tags {
                ...TagFragment
                __typename
              }
              options {
                ...EventOptions
                __typename
              }
              __typename
            }
            __typename
          }
        }
        fragment EventOptions on EventOptions {
          maximumAttendeeCapacity
          remainingAttendeeCapacity
          showRemainingAttendeeCapacity
          anonymousParticipation
          showStartTime
          showEndTime
          timezone
          offers {
            price
            priceCurrency
            url
            __typename
          }
          participationConditions {
            title
            content
            url
            __typename
          }
          attendees
          program
          commentModeration
          showParticipationPrice
          hideOrganizerWhenGroupEvent
          isOnline
          __typename
        }
        fragment TagFragment on Tag {
          id
          slug
          title
          __typename
        }
        fragment AdressFragment on Address {
          id
          description
          geom
          street
          locality
          postalCode
          region
          country
          type
          url
          originId
          timezone
          __typename
        }
        fragment ActorFragment on Actor {
          id
          avatar {
            id
            url
            __typename
          }
          type
          preferredUsername
          name
          domain
          summary
          url
          __typename
        }""",
}

EVENTS_HTU_HOST = 'events.htu.at'
EVENTS_HTU = f'https://{EVENTS_HTU_HOST}'


class Sync(tucal.Sync):
    events: List[Dict[str, Any]] = None

    def __init__(self, session: tuwien.sso.Session):
        super().__init__(session)

    def fetch(self):
        session = self.session.session
        r = session.post(f'{EVENTS_HTU}/api', json=QUERY)
        if r.status_code != 200:
            raise RuntimeError()

        raw_events = r.json()
        self.events = raw_events['data']['searchEvents']['elements']

    def store(self, cur: tucal.db.Cursor):
        group_nr = tucal.get_group_nr(cur, 'HTU Events', True)

        rows = [{
            'source': 'htu-events',
            'id': event['id'],
            'group': group_nr,
            'start': tucal.parse_iso_timestamp(event['beginsOn'], True),
            'end': tucal.parse_iso_timestamp(event['endsOn'], True) if event['endsOn'] else tucal.parse_iso_timestamp(event['beginsOn'], True) + datetime.timedelta(hours=1),
            'data': json.dumps({'htu': event}),
        } for event in self.events]

        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'start',
            'end_ts': 'end',
            'group_nr': 'group',
            'data': 'data',
        }
        tucal.db.upsert_values('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})
        ids_now = {row['id'] for row in rows}

        start_min = min([datetime.datetime.fromordinal(e['start'].toordinal()) for e in rows])

        cur.execute("LOCK TABLE tucal.external_event IN SHARE ROW EXCLUSIVE MODE")
        cur.execute("""
            SELECT event_id
            FROM tucal.external_event
            WHERE source = 'htu-events' AND NOT deleted AND
                  start_ts >= %s""", (start_min,))
        ids_db = {row[0] for row in cur.fetch_all()}

        ids_del = ids_db - ids_now
        cur.execute("""
            UPDATE tucal.external_event
            SET deleted = true
            WHERE source = 'htu-events' AND event_id = ANY(%s)""", (list(ids_del),))


class Plugin(tucal.Plugin):
    @staticmethod
    def sync() -> Sync:
        return Sync(tuwien.sso.Session())

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session) -> None:
        return None


"""
query FetchEvents($orderBy: EventOrderBy, $direction: SortDirection, $page: Int, $limit: Int) {
  events(orderBy: $orderBy, direction: $direction, page: $page, limit: $limit) {
    total
    elements {
      id
      uuid
      url
      local
      title
      description
      beginsOn
      endsOn
      status
      visibility
      insertedAt
      language
      picture {
        id
        url
        __typename
      }
      publishAt
      physicalAddress {
        ...AdressFragment
        __typename
      }
      organizerActor {
        ...ActorFragment
        __typename
      }
      attributedTo {
        ...ActorFragment
        __typename
      }
      category
      tags {
        ...TagFragment
        __typename
      }
      options {
        ...EventOptions
        __typename
      }
      __typename
    }
    __typename
  }
}
fragment AdressFragment on Address {
  id
  description
  geom
  street
  locality
  postalCode
  region
  country
  type
  url
  originId
  timezone
  __typename
}
fragment TagFragment on Tag {
  id
  slug
  title
  __typename
}
fragment EventOptions on EventOptions {
  maximumAttendeeCapacity
  remainingAttendeeCapacity
  showRemainingAttendeeCapacity
  anonymousParticipation
  showStartTime
  showEndTime
  timezone
  offers {
    price
    priceCurrency
    url
    __typename
  }
  participationConditions {
    title
    content
    url
    __typename
  }
  attendees
  program
  commentModeration
  showParticipationPrice
  hideOrganizerWhenGroupEvent
  isOnline
  __typename
}
fragment ActorFragment on Actor {
  id
  avatar {
    id
    url
    __typename
  }
  type
  preferredUsername
  name
  domain
  summary
  url
  __typename
"""
