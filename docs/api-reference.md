# Swedavia FlightInfo v2 – API reference

Source: the Swedavia developer portal (apideveloper.swedavia.se), the FlightInfo v2 operation
pages for all four endpoints, copied by Alex on 2026-11-24. This file is a cleaned-up copy:
content is unchanged, but shared object definitions are listed once instead of per endpoint.
Things the official pages contradict themselves on are marked **⚠**.

Base URL: `https://api.swedavia.se/flightinfo/v2`

## Common
- **Headers:** `Accept` is required on every operation (`application/json`; `application/xml` is
  also offered). The subscription key goes in `Ocp-Apim-Subscription-Key` (see research.md,
  "Access & authentication").
- **Dates in the URL:** RFC 3339 date only, `YYYY-MM-DD`.
- **Timestamps in responses:** strings in `date-time` format, UTC (fields ending in `Utc`).
- **Every field in every response is optional** (`Required: false`). Code must handle any of them
  being missing.

## Endpoints

| Operation | Request | Documented responses |
|---|---|---|
| Arrivals | `GET /{airportIATA}/arrivals/{date}` | 200, 204, 304, 400, 500 |
| Departures | `GET /{airportIATA}/departures/{date}` | 200, 204, 304, 400, 500 |
| Heartbeat | `GET /heartBeat[?evaluationId]` | 200 |
| Query | `GET /query[?filter][&continuationtoken][&count]` | 200 (429 above the rate limit) |

### GET arrivals
`GET /{airportIATA}/arrivals/{date}`

| Parameter | In | Required | Type | Description |
|---|---|---|---|---|
| `airportIATA` | path | yes | string | |
| `date` | path | yes | string | RFC 3339 date only, `YYYY-MM-DD` |

Responses: `200 OK` (`arrivals`), `204 No Content`, `304 Not Modified`, `400 Bad Request`,
`500 Internal Server Error`.

`arrivals` (response body):

| Field | Type | Description |
|---|---|---|
| `to` | `to` | The airport the list is for |
| `numberOfFlights` | integer (int32) | Number of flights in response |
| `flights` | `arrivalFlight[]` | A list with zero or more flights |

`to`:

| Field | Type | Description |
|---|---|---|
| `arrivalAirportIata` | string | IATA code for arrival airport |
| `arrivalAirportIcao` | string | ICAO code for arrival airport |
| `arrivalAirportSwedish` | string | Arrival airport name in Swedish |
| `arrivalAirportEnglish` | string | Arrival airport name in English |
| `flightArrivalDate` | string | Arrival date in UTC |

Example:
```json
{
    "to": {
        "arrivalAirportIata": "string",
        "arrivalAirportIcao": "string",
        "arrivalAirportSwedish": "string",
        "arrivalAirportEnglish": "string",
        "flightArrivalDate": "string"
    },
    "numberOfFlights": 0,
    "flights": [{
        "flightId": "string",
        "departureAirportSwedish": "string",
        "departureAirportEnglish": "string",
        "airlineOperator": {"iata": "string", "icao": "string", "name": "string"},
        "arrivalTime": {"scheduledUtc": "string", "estimatedUtc": "string", "actualUtc": "string"},
        "locationAndStatus": {
            "terminal": "string",
            "gate": "string",
            "flightLegStatus": "SCH",
            "flightLegStatusSwedish": "string",
            "flightLegStatusEnglish": "string"
        },
        "baggage": {
            "estimatedFirstBagUtc": "string",
            "baggageClaimUnit": "string",
            "firstBagUtc": "string",
            "lastBagUtc": "string"
        },
        "codeShareData": ["string"],
        "flightLegIdentifier": {
            "ifplId": "string",
            "callsign": "string",
            "aircraftRegistration": "string",
            "ssrCode": "string",
            "flightId": "string",
            "flightDepartureDateUtc": "string",
            "departureAirportIata": "string",
            "arrivalAirportIata": "string",
            "departureAirportIcao": "string",
            "arrivalAirportIcao": "string"
        },
        "remarksEnglish": [{"text": "string", "indicator": "string"}],
        "remarksSwedish": [{"text": "string", "indicator": "string"}],
        "viaDestinations": [{"airportIATA": "string", "airportSwedish": "string", "airportEnglish": "string"}],
        "diIndicator": "string"
    }]
}
```

### GET departures
`GET /{airportIATA}/departures/{date}`

Same parameters and responses as arrivals.

`departures` (response body):

| Field | Type | Description |
|---|---|---|
| `from` | `from` | The airport the list is for |
| `numberOfFlights` | integer (int32) | Number of flights in response |
| `flights` | `departureFlight[]` | A list with one or more flights **⚠** (arrivals say "zero or more") |

`from`:

| Field | Type | Description |
|---|---|---|
| `departureAirportIata` | string | IATA code for departure airport |
| `departureAirportIcao` | string | ICAO code for departure airport |
| `departureAirportSwedish` | string | Departure airport in Swedish |
| `departureAirportEnglish` | string | Departure airport in English |
| `flightDepartureDate` | string | Departure date in UTC |

Example:
```json
{
    "from": {
        "departureAirportIata": "string",
        "departureAirportIcao": "string",
        "departureAirportSwedish": "string",
        "departureAirportEnglish": "string",
        "flightDepartureDate": "string"
    },
    "numberOfFlights": 0,
    "flights": [{
        "flightId": "string",
        "arrivalAirportSwedish": "string",
        "arrivalAirportEnglish": "string",
        "airlineOperator": {"iata": "string", "icao": "string", "name": "string"},
        "departureTime": {"scheduledUtc": "string", "estimatedUtc": "string", "actualUtc": "string"},
        "locationAndStatus": {
            "terminal": "string",
            "gate": "string",
            "gateAction": "string",
            "gateActionSwedish": "string",
            "gateActionEnglish": "string",
            "gateOpenUtc": "string",
            "gateCloseUtc": "string",
            "flightLegStatus": "string",
            "flightLegStatusSwedish": "string",
            "flightLegStatusEnglish": "string"
        },
        "checkIn": {
            "checkInStatus": "string",
            "checkInStatusSwedish": "string",
            "checkInStatusEnglish": "string",
            "checkInDeskFrom": 0,
            "checkInDeskTo": 0
        },
        "codeShareData": ["string"],
        "flightLegIdentifier": {
            "ifplId": "string",
            "callsign": "string",
            "aircraftRegistration": "string",
            "ssrCode": "string",
            "flightId": "string",
            "flightDepartureDateUtc": "string",
            "departureAirportIata": "string",
            "arrivalAirportIata": "string",
            "departureAirportIcao": "string",
            "arrivalAirportIcao": "string"
        },
        "viaDestinations": [{"airportIATA": "string", "airportSwedish": "string", "airportEnglish": "string"}],
        "remarksEnglish": [{"text": "string", "indicator": "string"}],
        "remarksSwedish": [{"text": "string", "indicator": "string"}],
        "diIndicator": "string"
    }]
}
```

### GET heartBeat
`GET /heartBeat[?evaluationId]`

| Parameter | In | Required | Type | Description |
|---|---|---|---|---|
| `evaluationId` | query | no | integer (int32) | Not described further |

Response: `200 OK` with an empty JSON object:
```json
{}
```

### GET query
`GET /query[?filter][&continuationtoken][&count]`

Query flight information using an OData filter expression.

| Parameter | In | Required | Type | Description |
|---|---|---|---|---|
| `filter` | query | no | string | OData filter expression. Omit to get all flights |
| `continuationtoken` | query | no | string | Base64 encoded; must be URL-escaped by the client |
| `count` | query | no | integer (int32) | Number of items to return. **Default 25, max 1000** |

**Call limit:** one call per two seconds. Any additional call returns `429 Too Many Requests`.

**Supported filter fields:**

| Field | Meaning |
|---|---|
| `airport` | IATA code for any Swedavia airport |
| `flightType` | `A` for arrival, `D` for departure |
| `scheduled` | Local Swedish date for departure or arrival, written `YYMMDD` in the examples (e.g. `'190921'`) |
| `estimated` | UTC date and time for estimated departure or arrival (e.g. `'2019-07-02T08:30:00'`) |
| `flightStatus` | See documentation or response for status codes |
| `flightId` | Operator code and flight number |

**Supported operations:** `and`, `or`, `eq`, `ne`, `gt`, `ge`, `lt`, `le`.

**continuationtoken:** "Used for getting next set of flights. Use the value from your last result
to get updated flights. If no flights have been updated, you will get a result without flights.
You can store your continuationtoken locally and reuse it in a later call." In other words, it
returns *changes since the last call*, not the next page.

**Examples (verbatim):**
```
# Departures from Arlanda for 2019-09-21
airport eq 'ARN' and scheduled eq '190921' and flightType eq 'D'

# Arrivals at Arlanda and Visby for 2019-09-21
(airport eq 'ARN' or airport eq 'VBY') and flightType eq 'A' and scheduled eq '190921'

# Single flight
airport eq 'ARN' and scheduled eq '190921' and flightType eq 'D' and flightId eq 'SK007'

# Estimated times
airport eq 'ARN' and estimated eq '2019-07-02T08:30:00' and flightType eq 'D'

# Departures from Arlanda for a specific airline  ⚠ uses `type` and `airline`, which are not in the supported list
airport eq 'ARN' and type eq 'D' and airline eq 'SK'
```
To get all flights, leave the filter parameter empty.

`flightsResponse` (response body):

| Field | Type | Description |
|---|---|---|
| `flights` | `flight[]` | |
| `continuationtoken` | string | Pass back to get updated flights |

`flight` (one item):

| Field | Type | Description |
|---|---|---|
| `arrival` | `arrivalFlight` | Set when the item is an arrival |
| `departure` | `departureFlight` | Set when the item is a departure |
| `scheduledDate` | string | |

Example (flight objects shortened; they have the same shape as in arrivals/departures above):
```json
{
    "flights": [{
        "arrival": {"flightId": "string", "departureAirportEnglish": "string", "arrivalTime": {"scheduledUtc": "string"}},
        "departure": {"flightId": "string", "arrivalAirportEnglish": "string", "departureTime": {"scheduledUtc": "string"}},
        "scheduledDate": "string"
    }],
    "continuationtoken": "string"
}
```

## Object definitions

### arrivalFlight
| Field | Type | Description |
|---|---|---|
| `flightId` | string | Flight number |
| `departureAirportSwedish` | string | Departure airport name in Swedish |
| `departureAirportEnglish` | string | Departure airport name in English |
| `airlineOperator` | `airlineOperator` | |
| `arrivalTime` | `flightTime` | |
| `locationAndStatus` | `arrivalLocationAndStatus` | |
| `baggage` | `baggage` | |
| `codeShareData` | string[] | Alternate flightId |
| `flightLegIdentifier` | `flightLegIdentifier` | |
| `remarksEnglish` | `remark[]` | Remarks intended for FIDS screens in English |
| `remarksSwedish` | `remark[]` | Remarks intended for FIDS screens in Swedish |
| `viaDestinations` | `viaDestination[]` | Airports the flight lands at on the way to the final destination |
| `diIndicator` | string | Domestic (`D`), international (`I`) or Schengen (`S`) |

### departureFlight
| Field | Type | Description |
|---|---|---|
| `flightId` | string | Flight number |
| `arrivalAirportSwedish` | string | Arrival airport in Swedish |
| `arrivalAirportEnglish` | string | Arrival airport in English |
| `airlineOperator` | `airlineOperator` | |
| `departureTime` | `flightTime` | |
| `locationAndStatus` | `departureLocationAndStatus` | |
| `checkIn` | `checkIn` | |
| `codeShareData` | string[] | Alternate flightId |
| `flightLegIdentifier` | `flightLegIdentifier` | |
| `viaDestinations` | `viaDestination[]` | Airports the flight lands at on the way to the final destination |
| `remarksEnglish` | `remark[]` | Remarks intended for FIDS screens in English |
| `remarksSwedish` | `remark[]` | Remarks intended for FIDS screens in Swedish |
| `diIndicator` | string | Domestic (`D`), international (`I`) or Schengen (`S`) |

### airlineOperator
| Field | Type | Description |
|---|---|---|
| `iata` | string | The IATA code of the party operating the flight |
| `icao` | string | **⚠** Described as "the iata code" on the portal; presumably the ICAO code |
| `name` | string | The party operating the flight |

### flightTime (`arrivalTime` / `departureTime`)
Named `arrivalTime` and `departureTime` on the portal; the fields are identical.

| Field | Type | Description |
|---|---|---|
| `scheduledUtc` | string (date-time) | Scheduled time in UTC |
| `estimatedUtc` | string (date-time) | Estimated time in UTC |
| `actualUtc` | string (date-time) | Actual time in UTC |

### arrivalLocationAndStatus
| Field | Type | Description |
|---|---|---|
| `terminal` | string | Terminal identifier |
| `gate` | string | Uniquely defines one gate at the airport |
| `flightLegStatus` | string | The status of a flight leg (example value `SCH`) |
| `flightLegStatusSwedish` | string | Status text in Swedish |
| `flightLegStatusEnglish` | string | Status text in English |

### departureLocationAndStatus
| Field | Type | Description |
|---|---|---|
| `terminal` | string | Terminal identifier |
| `gate` | string | Uniquely defines one gate at the airport |
| `gateAction` | string | Boarding stage: open `O` or closed `C` |
| `gateActionSwedish` | string | Gate stage in Swedish |
| `gateActionEnglish` | string | Gate stage in English |
| `gateOpenUtc` | string (date-time) | When the gate opens for passenger processing |
| `gateCloseUtc` | string (date-time) | When the gate closes for passenger processing |
| `flightLegStatus` | string | The status of a flight leg |
| `flightLegStatusSwedish` | string | Status in Swedish |
| `flightLegStatusEnglish` | string | Status in English |

### baggage (arrivals only)
| Field | Type | Description |
|---|---|---|
| `estimatedFirstBagUtc` | string (date-time) | Not described |
| `baggageClaimUnit` | string | Baggage belt |
| `firstBagUtc` | string (date-time) | First bag on the belt, UTC |
| `lastBagUtc` | string (date-time) | Last bag on the belt, UTC |

### checkIn (departures only)
| Field | Type | Description |
|---|---|---|
| `checkInStatus` | string | Open `O` or closed `C` |
| `checkInStatusSwedish` | string | Check-in status in Swedish |
| `checkInStatusEnglish` | string | Check-in status in English |
| `checkInDeskFrom` | integer (int32) | First check-in desk |
| `checkInDeskTo` | integer (int32) | Last check-in desk |

### flightLegIdentifier
| Field | Type | Description |
|---|---|---|
| `ifplId` | string | Initial flight plan identifier |
| `callsign` | string | Identifies the aircraft in the airspace around an airport |
| `aircraftRegistration` | string | Unique aircraft identifier |
| `ssrCode` | string | Secondary surveillance radar code |
| `flightId` | string | Flight number |
| `flightDepartureDateUtc` | string (date-time) | Departure date in UTC |
| `departureAirportIata` | string | Departure airport IATA code |
| `arrivalAirportIata` | string | Arrival airport IATA code |
| `departureAirportIcao` | string | Departure airport ICAO code |
| `arrivalAirportIcao` | string | Arrival airport ICAO code |

### viaDestination
| Field | Type | Description |
|---|---|---|
| `airportIATA` | string | |
| `airportSwedish` | string | |
| `airportEnglish` | string | |

### remark
| Field | Type | Description |
|---|---|---|
| `text` | string | |
| `indicator` | string | |
