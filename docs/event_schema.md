# Event Schema

## JSON example
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_time": "2026-05-24T10:30:00Z",
  "event_name": "question_answered",
  "user_id": "u_12345",
  "session_id": "s_abc123",
  "source": "web",
  "status": "success",
  "payload": {
    "topic": "sql",
    "is_correct": true,
    "response_time_sec": 18
  }
}