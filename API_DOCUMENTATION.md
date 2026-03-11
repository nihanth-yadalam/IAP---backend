# Intelligent Academic Planner - API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication

Most endpoints require authentication using Bearer tokens. Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## Quick Reference: All Endpoints

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------| 
| POST | `/auth/login/access-token` | Login with credentials | ❌ |
| GET | `/auth/google/authorize` | Get Google OAuth URL | ✅ |
| GET | `/auth/google/callback` | OAuth callback handler | ❌ |
| POST | `/users/` | Register new user | ❌ |
| GET | `/users/me` | Get current user | ✅ |
| PUT | `/users/me/profile` | Update profile | ✅ |
| POST | `/users/me/password` | Change password | ✅ |
| POST | `/users/password-recovery/{email}` | Request password reset | ❌ |
| POST | `/users/reset-password/` | Reset password with token | ❌ |
| GET | `/onboarding/status` | Get onboarding progress | ✅ |
| POST | `/onboarding/questionnaire` | Submit questionnaire | ✅ |
| GET | `/courses/` | List courses | ✅ |
| POST | `/courses/` | Create course | ✅ |
| PATCH | `/courses/{id}` | Update course | ✅ |
| DELETE | `/courses/{id}` | Delete course | ✅ |
| GET | `/tasks/` | List tasks | ✅ |
| POST | `/tasks/` | Create task | ✅ |
| PATCH | `/tasks/{id}` | Update task | ✅ |
| DELETE | `/tasks/{id}` | Delete task | ✅ |
| GET | `/schedule/fixed` | List schedule slots | ✅ |
| POST | `/schedule/fixed` | Create recurring slots | ✅ |
| POST | `/schedule/slots` | Create calendar slot | ✅ |
| PUT | `/schedule/slots/{id}` | Update calendar slot | ✅ |
| DELETE | `/schedule/slots/{id}` | Delete calendar slot | ✅ |
| POST | `/sync/trigger` | Trigger manual sync | ✅ |
| GET | `/sync/status` | Get sync status | ✅ |
| POST | `/sync/reset/{user_id}` | Clear sync state | ✅ |
| POST | `/sync/push-all` | Push slots to Google | ✅ |
| POST | `/sync/initialize` | Initialize sync | ✅ |
| POST | `/webhooks/google-calendar` | Receive Google updates | ❌ |
| POST | `/webhooks/setup` | Setup webhook | ✅ |
| GET | `/admin/users` | List all users | ✅ |

---

## Table of Contents
1. [Authentication Endpoints](#authentication-endpoints)
2. [User Endpoints](#user-endpoints) 
3. [Onboarding Endpoints](#onboarding-endpoints)
4. [Course Endpoints](#course-endpoints)
5. [Task Endpoints](#task-endpoints)
6. [Schedule Endpoints](#schedule-endpoints)
7. [Calendar Sync Endpoints](#calendar-sync-endpoints)
8. [Webhook Endpoints](#webhook-endpoints)
9. [Admin Endpoints](#admin-endpoints)
10. [Error Responses](#error-responses)
11. [Data Models](#data-models)

---

## Authentication Endpoints

### 1. Login
Get access token for authentication.

**Endpoint:** `POST /auth/login/access-token`

**Authentication:** None required

**Request Body (Form Data):**
```
username: string (email or username)
password: string
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `400 Bad Request`: Incorrect email or password

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=secretpassword"
```

---

### 2. Get Google OAuth Authorization URL
Initiate Google OAuth flow to link Google Calendar.

**Endpoint:** `GET /auth/google/authorize`

**Authentication:** Required (Bearer Token)

**Query Parameters:** None

**Response:** `200 OK`
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/auth?...",
  "instructions": "Open this URL in your browser to authorize with Google"
}
```

**Error Responses:**
- `401 Unauthorized`: Invalid or missing token

**Example:**
```javascript
fetch('http://localhost:8000/api/v1/auth/google/authorize', {
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

**Next Step:** Open the returned `authorization_url` in browser. Google will redirect to `/auth/google/callback`.

---

### 3. Google OAuth Callback
Handles OAuth callback and stores refresh token.

**Endpoint:** `GET /auth/google/callback`

**Authentication:** None required

**Query Parameters:**
- `code`: Authorization code from Google
- `state`: User ID for verification

**Response:** Redirects to frontend with status

**Note:** This endpoint is called automatically by Google after user grants permission. The backend stores the refresh token and initializes calendar sync.

---

## User Endpoints

### 1. Create User (Register)
Create a new user account.

**Endpoint:** `POST /users/`

**Authentication:** None required

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "google_linked": false,
  "profile": {
    "full_name": null,
    "major": null,
    "university": null,
    "timezone": "UTC",
    "current_archetype": "Unclassified",
    "onboarding_data": {}
  }
}
```

**Error Responses:**
- `400 Bad Request`: Email or username already exists

**Example:**
```javascript
fetch('http://localhost:8000/api/v1/users/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    email: 'user@example.com',
    username: 'johndoe',
    password: 'securepassword123'
  })
})
```

---

### 2. Get Current User
Retrieve the authenticated user's information.

**Endpoint:** `GET /users/me`

**Authentication:** Required (Bearer Token)

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "google_linked": true,
  "profile": {
    "full_name": "John Doe",
    "major": "Computer Science",
    "university": "Example University",
    "timezone": "UTC",
    "current_archetype": "Balanced Learner",
    "onboarding_data": {
      "chronotype": "morning",
      "study_block_duration": 90,
      "subject_confidences": {
        "55": {
          "subject_name": "Math",
          "confidence_score": 8,
          "duration_multiplier": 1.5,
          "drain_rate": 5
        }
      }
    }
  }
}
```

**Example:**
```javascript
fetch('http://localhost:8000/api/v1/users/me', {
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

---

### 3. Update User Profile
Update the current user's profile information.

**Endpoint:** `PUT /users/me/profile`

**Authentication:** Required (Bearer Token)

**Request Body:** (All fields optional)
```json
{
  "full_name": "John Doe",
  "major": "Computer Science",
  "university": "Example University",
  "timezone": "UTC",
  "current_archetype": "Balanced Learner"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "google_linked": true,
  "profile": {
    "full_name": "John Doe",
    "major": "Computer Science",
    "university": "Example University",
    "timezone": "UTC",
    "current_archetype": "Balanced Learner",
    "onboarding_data": {}
  }
}
```

---

### 4. Update Password
Change the current user's password.

**Endpoint:** `POST /users/me/password`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "current_password": "oldpassword123",
  "new_password": "newpassword456"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password updated successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Incorrect current password
- `400 Bad Request`: New password cannot be the same as current password

---

### 5. Password Recovery (Request Reset)
Request a password reset token.

**Endpoint:** `POST /users/password-recovery/{email}`

**Authentication:** None required

**Path Parameters:**
- `email`: User's email address

**Response:** `200 OK`
```json
{
  "message": "Password recovery email sent (check terminal)"
}
```

**Note:** In development, the reset token is printed to the server terminal for testing purposes.

**Error Responses:**
- `404 Not Found`: User with this email does not exist

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/users/password-recovery/user@example.com"
```

---

### 6. Reset Password
Reset password using the recovery token.

**Endpoint:** `POST /users/reset-password/`

**Authentication:** None required

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "email": "user@example.com",
  "new_password": "newsecurepassword123"
}
```

**Response:** `200 OK`
```json
{
  "message": "Password updated successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid token
- `404 Not Found`: User does not exist

---

## Onboarding Endpoints

### 1. Get Onboarding Status
Check the user's onboarding progress.

**Endpoint:** `GET /onboarding/status`

**Authentication:** Required (Bearer Token)

**Response:** `200 OK`

**Possible responses:**

Not started (questionnaire pending):
```json
{
  "is_complete": false,
  "step": "questionnaire"
}
```

Questionnaire completed, schedule pending:
```json
{
  "is_complete": false,
  "step": "schedule"
}
```

Fully completed:
```json
{
  "is_complete": true,
  "step": "done"
}
```

---

### 2. Submit Onboarding Questionnaire
Submit answers to the initial profiling questionnaire ("Cold Start" solution).

**Endpoint:** `POST /onboarding/questionnaire`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "chronotype": "morning",
  "study_block_duration": 90,
  "subject_confidences": [
    {
      "subject_name": "Mathematics",
      "confidence_score": 8,
      "duration_multiplier": 1.5,
      "drain_rate": 5
    },
    {
      "subject_name": "Physics",
      "confidence_score": 7,
      "duration_multiplier": 1.2,
      "drain_rate": 4
    }
  ]
}
```

**Field Details:**
- `chronotype`: `"morning"`, `"evening"`, or `"neutral"` — affects task scheduling strategy
- `study_block_duration`: Integer, preferred study duration in minutes (e.g., 90)
- `subject_confidences`: Array of subject confidence profiles
  - `subject_name`: Course/subject name (string)
  - `confidence_score`: 1-10 scale
  - `duration_multiplier`: Estimated multiplier (e.g., 1.5 = +50% more time needed)
  - `drain_rate`: 1-5 scale, how draining the subject is

**Response:** `200 OK`
```json
{
  "message": "Onboarding questionnaire saved successfully",
  "step": "schedule"
}
```

**Error Responses:**
- `400 Bad Request`: Invalid confidence scores (must be 1-10)
- `404 Not Found`: User profile not found

**Example:**
```javascript
fetch('http://localhost:8000/api/v1/onboarding/questionnaire', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    chronotype: 'morning',
    study_block_duration: 90,
    subject_confidences: [
      {
        subject_name: 'Math',
        confidence_score: 8,
        duration_multiplier: 1.5,
        drain_rate: 5
      }
    ]
  })
})
```

---

## Course Endpoints

### 1. Get All Courses
Retrieve all active (non-archived) courses for the current user.

**Endpoint:** `GET /courses/`

**Authentication:** Required (Bearer Token)

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "name": "Calculus I",
    "code": "MATH201",
    "term": "Spring 2026",
    "color_code": "#FF5733",
    "is_archived": false
  },
  {
    "id": 2,
    "user_id": 1,
    "name": "Physics 101",
    "code": "PHYS101",
    "term": "Spring 2026",
    "color_code": "#33C1FF",
    "is_archived": false
  }
]
```

**Example:**
```javascript
fetch('http://localhost:8000/api/v1/courses/?skip=0&limit=100', {
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

---

### 2. Create Course
Create a new course.

**Endpoint:** `POST /courses/`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "name": "Data Structures",
  "code": "CS301",
  "term": "Spring 2026",
  "color_code": "#4CAF50",
  "is_archived": false
}
```

**Field Details:**
- `name`: Course name (must be unique per user, required)
- `code`: Course code (optional)
- `term`: Term/semester (optional)
- `color_code`: Hex color code for UI display
- `is_archived`: Whether the course is archived (default: false)

**Response:** `200 OK`
```json
{
  "id": 3,
  "user_id": 1,
  "name": "Data Structures",
  "code": "CS301",
  "term": "Spring 2026",
  "color_code": "#4CAF50",
  "is_archived": false
}
```

**Error Responses:**
- `400 Bad Request`: Course with this name already exists

---

### 3. Update Course
Update an existing course.

**Endpoint:** `PATCH /courses/{id}`

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `id`: Course ID

**Request Body:** (All fields optional)
```json
{
  "name": "Advanced Data Structures",
  "code": "CS401",
  "term": "Fall 2026",
  "color_code": "#8BC34A",
  "is_archived": true
}
```

**Response:** `200 OK`
```json
{
  "id": 3,
  "user_id": 1,
  "name": "Advanced Data Structures",
  "code": "CS401",
  "term": "Fall 2026",
  "color_code": "#8BC34A",
  "is_archived": true
}
```

**Error Responses:**
- `404 Not Found`: Course not found
- `400 Bad Request`: Course name already exists

---

### 4. Delete Course
Permanently delete a course.

**Endpoint:** `DELETE /courses/{id}`

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `id`: Course ID

**Response:** `200 OK`
```json
{
  "message": "Course deleted successfully"
}
```

**Error Responses:**
- `404 Not Found`: Course not found

---

## Task Endpoints

### 1. Get All Tasks
Retrieve tasks with optional date filtering.

**Endpoint:** `GET /tasks/`

**Authentication:** Required (Bearer Token)

**Query Parameters:**
- `start_date`: ISO 8601 datetime (optional)
- `end_date`: ISO 8601 datetime (optional)
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)

**Filtering Logic:**
- If date range provided: Returns tasks with `deadline` within range
- If no date range: Returns all tasks

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Complete Assignment 3",
    "description": "Solve problems 1-10",
    "priority": "High",
    "category": "Assignment",
    "status": "Pending",
    "deadline": "2026-02-15T23:59:00",
    "scheduled_start_time": "2026-02-14T14:00:00",
    "scheduled_end_time": "2026-02-14T16:00:00",
    "estimated_duration_mins": 120,
    "course_id": 1,
    "google_event_id": "abc123xyz",
    "created_at": "2026-02-10T10:30:00",
    "course": {
      "id": 1,
      "name": "Calculus I",
      "code": "MATH201",
      "term": "Spring 2026",
      "color_code": "#FF5733"
    }
  }
]
```

**Example:**
```javascript
// Get tasks between specific dates
const startDate = '2026-02-10T00:00:00';
const endDate = '2026-02-17T23:59:59';
fetch(`http://localhost:8000/api/v1/tasks/?start_date=${startDate}&end_date=${endDate}`, {
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

---

### 2. Create Task
Create a new task (Story 3.1: Manual Task Entry).

**Endpoint:** `POST /tasks/`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "title": "Study for Midterm",
  "description": "Review chapters 1-5",
  "priority": "High",
  "category": "Exam",
  "status": "Pending",
  "deadline": "2026-02-20T09:00:00",
  "scheduled_start_time": "2026-02-18T10:00:00",
  "scheduled_end_time": "2026-02-18T12:00:00",
  "estimated_duration_mins": 120,
  "course_id": 1
}
```

**Field Details:**
- `title`: Task title (required)
- `description`: Task description (optional)
- `priority`: `"High"`, `"Medium"`, or `"Low"` (default: "Medium")
- `category`: `"Assignment"`, `"Exam"`, `"Project"`, or `"Study"` (default: "Study")
- `status`: `"Pending"`, `"In_Progress"`, or `"Completed"` (default: "Pending")
- `deadline`: ISO 8601 datetime (optional)
- `scheduled_start_time`: ISO 8601 datetime (optional, must be paired with end_time)
- `scheduled_end_time`: ISO 8601 datetime (optional, must be paired with start_time)
- `estimated_duration_mins`: Integer (optional)
- `course_id`: Foreign key to course (optional)

**Validation Rules:**
- If `scheduled_start_time` is provided, `scheduled_end_time` must also be provided (and vice versa)
- `scheduled_end_time` must be after `scheduled_start_time`
- **Collision Detection**: The system checks for time slot overlaps with:
  - Other tasks
  - Fixed schedule slots (recurring weekly commitments)
  - Google Calendar events (if synced)

**Response:** `200 OK`
```json
{
  "id": 2,
  "user_id": 1,
  "title": "Study for Midterm",
  "description": "Review chapters 1-5",
  "priority": "High",
  "category": "Exam",
  "status": "Pending",
  "deadline": "2026-02-20T09:00:00",
  "scheduled_start_time": "2026-02-18T10:00:00",
  "scheduled_end_time": "2026-02-18T12:00:00",
  "estimated_duration_mins": 120,
  "course_id": 1,
  "google_event_id": null,
  "created_at": "2026-02-10T11:00:00",
  "course": {
    "id": 1,
    "name": "Calculus I",
    "code": "MATH201",
    "term": "Spring 2026",
    "color_code": "#FF5733"
  }
}
```

**Error Responses:**
- `400 Bad Request`: Validation errors (missing required paired fields)
- `404 Not Found`: Course not found
- `409 Conflict`: Time slot overlaps with existing task or fixed schedule

**Collision Error Example:**
```json
{
  "detail": "Time slot overlaps with: 'Complete Assignment 3' (2026-02-14T14:00:00 - 2026-02-14T16:00:00)"
}
```

**Auto-Sync to Google Calendar:**
- If user has linked Google Calendar (`google_refresh_token` present), the task is automatically created as a Google Calendar event
- `google_event_id` is populated on response

---

### 3. Update Task
Update an existing task.

**Endpoint:** `PATCH /tasks/{id}`

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `id`: Task ID

**Request Body:** (All fields optional)
```json
{
  "title": "Study for Final Exam",
  "status": "In_Progress",
  "priority": "High",
  "scheduled_start_time": "2026-02-18T14:00:00",
  "scheduled_end_time": "2026-02-18T16:00:00"
}
```

**Response:** `200 OK`
```json
{
  "id": 2,
  "user_id": 1,
  "title": "Study for Final Exam",
  "description": "Review chapters 1-5",
  "priority": "High",
  "category": "Exam",
  "status": "In_Progress",
  "deadline": "2026-02-20T09:00:00",
  "scheduled_start_time": "2026-02-18T14:00:00",
  "scheduled_end_time": "2026-02-18T16:00:00",
  "estimated_duration_mins": 120,
  "course_id": 1,
  "google_event_id": "abc123xyz",
  "created_at": "2026-02-10T11:00:00",
  "course": {
    "id": 1,
    "name": "Calculus I",
    "code": "MATH201",
    "term": "Spring 2026",
    "color_code": "#FF5733"
  }
}
```

**Error Responses:**
- `404 Not Found`: Task not found
- `409 Conflict`: Updated time slot overlaps with existing task or fixed schedule

**Note:** 
- Collision checking is performed when scheduled times are modified
- If Google Calendar linked, the event is updated in Google Calendar
- If `status` changed to `Completed`, the task remains in database for history/analytics

---

### 4. Delete Task
Permanently delete a task.

**Endpoint:** `DELETE /tasks/{id}`

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `id`: Task ID

**Response:** `200 OK`
```json
{
  "message": "Task deleted successfully"
}
```

**Error Responses:**
- `404 Not Found`: Task not found

**Note:** If task has associated Google Calendar event, it is also deleted from Google Calendar.

---

## Schedule Endpoints

### 1. Get Fixed Schedule
Retrieve all fixed schedule slots (recurring weekly commitments and calendar events).

**Endpoint:** `GET /schedule/fixed`

**Authentication:** Required (Bearer Token)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "title": "Calculus Lecture",
    "label": "Calculus Lecture",
    "day_of_week": "Monday",
    "start_time": "09:00:00",
    "end_time": "11:00:00",
    "is_google_event": false,
    "google_event_id": null,
    "last_updated_source": null,
    "is_deleted": false
  },
  {
    "id": 2,
    "user_id": 1,
    "title": "Physics Lab",
    "label": "Physics Lab",
    "day_of_week": "Wednesday",
    "start_time": "14:00:00",
    "end_time": "16:00:00",
    "is_google_event": false,
    "google_event_id": null,
    "last_updated_source": null,
    "is_deleted": false
  }
]
```

**Example:**
```javascript
fetch('http://localhost:8000/api/v1/schedule/fixed', {
  headers: {
    'Authorization': 'Bearer ' + accessToken
  }
})
```

---

### 2. Create Fixed Schedule (Bulk Insert)
Add recurring weekly fixed schedule slots (onboarding Story 2.3).

**Endpoint:** `POST /schedule/fixed`

**Authentication:** Required (Bearer Token)

**Request Body:** Array of recurring slots
```json
[
  {
    "day_of_week": "Monday",
    "start_time": "09:00:00",
    "end_time": "11:00:00",
    "label": "Calculus Lecture",
    "is_google_event": false,
    "google_event_id": null
  },
  {
    "day_of_week": "Wednesday",
    "start_time": "14:00:00",
    "end_time": "15:30:00",
    "label": "Physics Lab",
    "is_google_event": false,
    "google_event_id": null
  }
]
```

**Field Details:**
- `day_of_week`: `"Monday"`, `"Tuesday"`, `"Wednesday"`, `"Thursday"`, `"Friday"`, `"Saturday"`, or `"Sunday"`
- `start_time`: Time in HH:MM:SS format (24-hour)
- `end_time`: Time in HH:MM:SS format (24-hour)
- `label`: Description of the fixed slot
- `is_google_event`: Boolean indicating if imported from Google Calendar (default: false)
- `google_event_id`: Google Calendar event ID (optional)

**Response:** `200 OK`
```json
{
  "message": "Successfully added 2 fixed slots."
}
```

**Example:**
```javascript
fetch('http://localhost:8000/api/v1/schedule/fixed', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + accessToken,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify([
    {
      day_of_week: 'Monday',
      start_time: '09:00:00',
      end_time: '11:00:00',
      label: 'Calculus Lecture',
      is_google_event: false
    }
  ])
})
```

**Important Note:** This endpoint **replaces** all existing recurring slots (non-Google events). Use as a bulk update endpoint for onboarding.

---

### 3. Create Calendar Slot
Create a single calendar event slot (specific date/time).

**Endpoint:** `POST /schedule/slots`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "title": "Study Session",
  "google_start_datetime": "2026-02-15T14:00:00",
  "google_end_datetime": "2026-02-15T16:00:00"
}
```

**Field Details:**
- `title`: Event title (required)
- `google_start_datetime`: Start time ISO 8601 format (required)
- `google_end_datetime`: End time ISO 8601 format (required)

**Response:** `200 OK`
```json
{
  "id": 10,
  "user_id": 1,
  "title": "Study Session",
  "label": null,
  "day_of_week": null,
  "start_time": null,
  "end_time": null,
  "google_start_datetime": "2026-02-15T14:00:00",
  "google_end_datetime": "2026-02-15T16:00:00",
  "is_google_event": false,
  "google_event_id": "gcal_event_123",
  "last_updated_source": "local",
  "is_deleted": false
}
```

**Auto-Sync:** If user has Google Calendar linked, event is automatically created in Google Calendar.

---

### 4. Update Calendar Slot
Update an existing calendar slot.

**Endpoint:** `PUT /schedule/slots/{id}`

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `id`: Slot ID

**Request Body:** (All fields optional)
```json
{
  "title": "Extended Study Session",
  "google_start_datetime": "2026-02-15T13:00:00",
  "google_end_datetime": "2026-02-15T17:00:00"
}
```

**Response:** `200 OK`
```json
{
  "id": 10,
  "user_id": 1,
  "title": "Extended Study Session",
  "label": null,
  "day_of_week": null,
  "start_time": null,
  "end_time": null,
  "google_start_datetime": "2026-02-15T13:00:00",
  "google_end_datetime": "2026-02-15T17:00:00",
  "is_google_event": false,
  "google_event_id": "gcal_event_123",
  "last_updated_source": "local",
  "is_deleted": false
}
```

**Error Responses:**
- `404 Not Found`: Slot not found

---

### 5. Delete Calendar Slot
Delete a calendar slot.

**Endpoint:** `DELETE /schedule/slots/{id}`

**Authentication:** Required (Bearer Token)

**Path Parameters:**
- `id`: Slot ID

**Response:** `200 OK`
```json
{
  "message": "Schedule slot deleted successfully"
}
```

**Error Responses:**
- `404 Not Found`: Slot not found

**Note:** If the slot has a Google Calendar event, it is also deleted from Google Calendar.

---

## Calendar Sync Endpoints

### 1. Get Sync Status
Get the current synchronization status with Google Calendar.

**Endpoint:** `GET /sync/status`

**Authentication:** Required (Bearer Token)

**Response:** `200 OK`
```json
{
  "user_id": 1,
  "google_calendar_id": "user@gmail.com",
  "sync_token": "ABC123xyz456",
  "last_sync_at": "2026-02-18T10:30:00",
  "webhook_channel_id": "channel_123",
  "webhook_expiration": "2026-02-25T10:30:00"
}
```

**Error Responses:**
- `400 Bad Request`: User has not completed Google OAuth

---

### 2. Trigger Manual Sync
Manually pull latest events from Google Calendar (incremental sync).

**Endpoint:** `POST /sync/trigger`

**Authentication:** Required (Bearer Token)

**Request Body:** None

**Response:** `200 OK`
```json
{
  "status": "sync_completed",
  "user_id": 1,
  "synced_at": "2026-02-18T10:35:00"
}
```

**Error Responses:**
- `400 Bad Request`: User has not completed Google OAuth

**How it Works:**
1. Uses stored `sync_token` for incremental sync
2. Fetches only changes since last sync
3. Imports events as fixed schedule slots
4. Updates local database

---

### 3. Reset Sync State
Clear sync token to force full calendar resync.

**Endpoint:** `POST /sync/reset/{user_id}`

**Authentication:** Required (Bearer Token, Admin)

**Path Parameters:**
- `user_id`: User ID to reset

**Response:** `200 OK`
```json
{
  "message": "Sync state reset. Next sync will be a full import."
}
```

**Use Case:** If sync gets out of sync with Google Calendar, reset to force full re-import.

---

### 4. Push All Local Slots to Google
Push all local calendar slots to Google Calendar.

**Endpoint:** `POST /sync/push-all`

**Authentication:** Required (Bearer Token)

**Request Body:** None

**Response:** `200 OK`
```json
{
  "status": "push_completed",
  "user_id": 1,
  "pushed_count": 5,
  "pushed_at": "2026-02-18T10:40:00"
}
```

**Use Case:** After creating/updating multiple slots locally, push all to Google at once.

---

### 5. Initialize Sync
Re-initialize calendar sync after OAuth.

**Endpoint:** `POST /sync/initialize`

**Authentication:** Required (Bearer Token)

**Request Body:** None

**Response:** `200 OK`
```json
{
  "status": "sync_initialized",
  "user_id": 1,
  "initialized_at": "2026-02-18T10:45:00"
}
```

**Use Case:** Called automatically after OAuth callback, but can be called manually if needed.

---

## Webhook Endpoints

### 1. Receive Google Calendar Updates
Webhook endpoint to receive push notifications from Google Calendar when events change.

**Endpoint:** `POST /webhooks/google-calendar`

**Authentication:** None required (verified by Google headers)

**Headers Received:**
- `X-Goog-Channel-ID`: Webhook channel ID
- `X-Goog-Resource-State`: Notification state (exists, sync)

**Response:** `204 No Content`

**How it Works:**
1. Google sends notification when calendar changes
2. Backend verifies webhook validity
3. Triggers `sync_from_google()` automatically
4. Local database updated with latest Google events

**Note:** Webhooks expire after 7 days and are auto-renewed by APScheduler background task.

---

### 2. Setup Webhook
Manually setup webhook channel for receiving Google Calendar updates.

**Endpoint:** `POST /webhooks/setup`

**Authentication:** Required (Bearer Token)

**Request Body:** None

**Response:** `200 OK`
```json
{
  "status": "webhook_setup_completed",
  "user_id": 1,
  "channel_id": "channel_abc123",
  "expiration": "2026-02-25T11:00:00"
}
```

**Use Case:** Called automatically during OAuth, but can be manually triggered if webhook expires.

---

## Admin Endpoints

### 1. List All Users
Get list of all users in the system (admin only).

**Endpoint:** `GET /admin/users`

**Authentication:** Required (Bearer Token, Admin)

**Query Parameters:**
- `skip`: Number of users to skip (default: 0)
- `limit`: Maximum users to return (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "email": "user1@example.com",
    "username": "johndoe",
    "google_linked": true,
    "profile": {
      "full_name": "John Doe",
      "major": "Computer Science",
      "university": "Example University",
      "timezone": "UTC",
      "current_archetype": "Balanced Learner",
      "onboarding_data": {}
    }
  },
  {
    "id": 2,
    "email": "user2@example.com",
    "username": "janedoe",
    "google_linked": false,
    "profile": {
      "full_name": "Jane Doe",
      "major": "Biology",
      "university": "Example University",
      "timezone": "UTC",
      "current_archetype": "Unclassified",
      "onboarding_data": {}
    }
  }
]
```

**Error Responses:**
- `403 Forbidden`: User is not an admin

---

## Error Responses

### Standard HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created
- `204 No Content`: Successful request with no response body
- `400 Bad Request`: Invalid request data or validation error
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Authenticated but not authorized (e.g., not admin)
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate, time slot collision)
- `422 Unprocessable Entity`: Validation error (Pydantic)
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Examples

**Authentication Error:**
```json
{
  "detail": "Could not validate credentials"
}
```

**Validation Error (Pydantic):**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ]
}
```

**Resource Not Found:**
```json
{
  "detail": "Task not found"
}
```

**Time Collision Error:**
```json
{
  "detail": "Time slot overlaps with: 'Complete Assignment 3' (2026-02-14T14:00:00 - 2026-02-14T16:00:00)"
}
```

**Duplicate Resource:**
```json
{
  "detail": "The user with this email already exists in the system."
}
```

**OAuth Not Completed:**
```json
{
  "detail": "User has not completed Google OAuth"
}
```

---

## Data Models

### Enums

#### Priority Level
```
"High" | "Medium" | "Low"
```

#### Task Category
```
"Assignment" | "Exam" | "Project" | "Study"
```

#### Task Status
```
"Pending" | "In_Progress" | "Completed"
```

#### Chronotype
```
"morning" | "evening" | "neutral"
```

#### Day of Week
```
"Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday"
```

### Core Data Structures

#### User
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "google_linked": true,
  "profile": {
    "full_name": "John Doe",
    "major": "Computer Science",
    "university": "Example University",
    "timezone": "UTC",
    "current_archetype": "Balanced Learner",
    "onboarding_data": {}
  }
}
```

#### Task
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Complete Assignment 3",
  "description": "Solve problems 1-10",
  "priority": "High",
  "category": "Assignment",
  "status": "Pending",
  "deadline": "2026-02-15T23:59:00",
  "scheduled_start_time": "2026-02-14T14:00:00",
  "scheduled_end_time": "2026-02-14T16:00:00",
  "estimated_duration_mins": 120,
  "course_id": 1,
  "google_event_id": "abc123",
  "created_at": "2026-02-10T10:30:00",
  "course": {
    "id": 1,
    "name": "Calculus I",
    "code": "MATH201",
    "term": "Spring 2026",
    "color_code": "#FF5733"
  }
}
```

#### Course
```json
{
  "id": 1,
  "user_id": 1,
  "name": "Calculus I",
  "code": "MATH201",
  "term": "Spring 2026",
  "color_code": "#FF5733",
  "is_archived": false
}
```

#### Schedule Slot
```json
{
  "id": 1,
  "user_id": 1,
  "title": "Calculus Lecture",
  "label": "Calculus Lecture",
  "day_of_week": "Monday",
  "start_time": "09:00:00",
  "end_time": "11:00:00",
  "google_start_datetime": null,
  "google_end_datetime": null,
  "is_google_event": false,
  "google_event_id": null,
  "last_updated_source": null,
  "is_deleted": false
}
```

---

## Integration Guidelines

### 1. Authentication Flow

```javascript
// 1. Register new user
const registerResponse = await fetch('http://localhost:8000/api/v1/users/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    username: 'johndoe',
    password: 'password123'
  })
});

// 2. Login to get token
const loginFormData = new FormData();
loginFormData.append('username', 'user@example.com');
loginFormData.append('password', 'password123');

const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login/access-token', {
  method: 'POST',
  body: loginFormData
});

const { access_token } = await loginResponse.json();

// 3. Store token
localStorage.setItem('token', access_token);

// 4. Use token in subsequent requests
const userResponse = await fetch('http://localhost:8000/api/v1/users/me', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

### 2. Onboarding Flow

```javascript
// 1. Check onboarding status
const status = await fetch('http://localhost:8000/api/v1/onboarding/status', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

if (!status.is_complete) {
  if (status.step === 'questionnaire') {
    // Show questionnaire form
    
    // 2. Submit questionnaire
    await fetch('http://localhost:8000/api/v1/onboarding/questionnaire', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        chronotype: 'morning',
        study_block_duration: 90,
        subject_confidences: [
          {
            subject_name: 'Math',
            confidence_score: 8,
            duration_multiplier: 1.5,
            drain_rate: 5
          }
        ]
      })
    });
  }
  
  if (status.step === 'schedule') {
    // Show schedule setup
    
    // 3. Create fixed schedule
    await fetch('http://localhost:8000/api/v1/schedule/fixed', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify([
        {
          day_of_week: 'Monday',
          start_time: '09:00:00',
          end_time: '11:00:00',
          label: 'Calculus Lecture',
          is_google_event: false
        }
      ])
    });
  }
}
```

### 3. Google Calendar Integration Flow

```javascript
// 1. Get OAuth authorization URL
const authResponse = await fetch('http://localhost:8000/api/v1/auth/google/authorize', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

// 2. Open URL for user consent
window.open(authResponse.authorization_url, '_blank');

// 3. After user grants permission, backend stores token
// User is redirected to frontend (you'll receive callback via URL params)

// 4. Check sync status
const syncStatus = await fetch('http://localhost:8000/api/v1/sync/status', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

// 5. Manually trigger sync when needed
await fetch('http://localhost:8000/api/v1/sync/trigger', {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### 4. Task Management Example (Story 3.1: Manual Entry)

```javascript
// 1. Create a course first
const course = await fetch('http://localhost:8000/api/v1/courses/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Calculus I',
    code: 'MATH201',
    term: 'Spring 2026',
    color_code: '#FF5733',
    is_archived: false
  })
}).then(r => r.json());

// 2. Create a task manually
const task = await fetch('http://localhost:8000/api/v1/tasks/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    title: 'Complete Assignment 1',
    description: 'Problems 1-10',
    priority: 'High',
    category: 'Assignment',
    status: 'Pending',
    deadline: '2026-02-20T23:59:00',
    scheduled_start_time: '2026-02-15T14:00:00',
    scheduled_end_time: '2026-02-15T16:00:00',
    estimated_duration_mins: 120,
    course_id: course.id
  })
}).then(r => r.json());

// 3. Update task status
await fetch(`http://localhost:8000/api/v1/tasks/${task.id}`, {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    status: 'Completed'
  })
});

// 4. Delete task if needed
await fetch(`http://localhost:8000/api/v1/tasks/${task.id}`, {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### 5. Date/Time Handling

All datetime fields use ISO 8601 format:
```
"2026-02-14T14:00:00"
```

Convert JavaScript Date objects:
```javascript
// To ISO string
const isoString = new Date().toISOString().slice(0, 19); // Remove milliseconds

// Parse ISO string
const date = new Date('2026-02-14T14:00:00');
```

### 6. Error Handling Best Practices

```javascript
async function apiCall(url, options) {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const error = await response.json();
      
      if (response.status === 401) {
        // Redirect to login
        window.location.href = '/login';
      } else if (response.status === 409) {
        // Handle conflicts (e.g., time collision)
        alert(error.detail);
      } else if (response.status === 400) {
        // Handle validation errors
        if (Array.isArray(error.detail)) {
          error.detail.forEach(err => console.error(`${err.loc.join('.')}: ${err.msg}`));
        } else {
          console.error(error.detail);
        }
      } else {
        // Handle other errors
        console.error(error.detail);
      }
      
      throw new Error(error.detail);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
```

---

## Interactive API Documentation

When the server is running, you can access interactive API documentation at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These provide interactive interfaces to test all endpoints directly from your browser.

---

## Token Management

- **Access Token Expiration**: 30 minutes (default)
- **Token Type**: JWT (JSON Web Token)
- **Refresh**: Tokens expire and require re-login. No refresh token endpoint currently implemented.

### Best Practices

1. Store token in secure storage (httpOnly cookie or secure localStorage)
2. Include token in all authenticated requests
3. Handle 401 responses by redirecting to login
4. Implement token expiration checking on client side

---

## Rate Limiting & Performance

- No rate limiting currently implemented
- Pagination available on list endpoints via `skip` and `limit` parameters
- Default limit: 100 items per request
- Recommended: Implement frontend pagination for large datasets
- Time complexity of collision checking: O(n) where n = existing slots on that day

---

**Last Updated:** February 18, 2026  
**API Version:** 1.0 (Beta)  
**Current Sprint:** Epic 1, 2, and Story 3.1 Complete
