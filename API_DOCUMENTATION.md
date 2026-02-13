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

## Table of Contents
1. [Authentication Endpoints](#authentication-endpoints)
2. [User Endpoints](#user-endpoints) 
3. [Onboarding Endpoints](#onboarding-endpoints)
4. [Course Endpoints](#course-endpoints)
5. [Task Endpoints](#task-endpoints)
6. [Schedule Endpoints](#schedule-endpoints)
7. [Error Responses](#error-responses)
8. [Data Models](#data-models)

---

## Authentication Endpoints

### 1. Login
Get access token for authentication.

**Endpoint:** `POST /login/access-token`

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
curl -X POST "http://localhost:8000/api/v1/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=secretpassword"
```

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
  "profile": {
    "full_name": null,
    "major": null,
    "university": null,
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
  "profile": {
    "full_name": "John Doe",
    "major": "Computer Science",
    "university": "Example University",
    "current_archetype": "Balanced Learner",
    "onboarding_data": {
      "chronotype": "morning",
      "study_style": "pomodoro",
      "subject_confidences": {
        "Math": 8,
        "Physics": 6
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
  "current_archetype": "Balanced Learner"
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "profile": {
    "full_name": "John Doe",
    "major": "Computer Science",
    "university": "Example University",
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
- `400 Bad Request`: Incorrect password
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

**Note:** In the current implementation, the reset token is printed to the server terminal for testing purposes.

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

Not started:
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
Submit answers to the onboarding questionnaire.

**Endpoint:** `POST /onboarding/questionnaire`

**Authentication:** Required (Bearer Token)

**Request Body:**
```json
{
  "chronotype": "morning",
  "study_style": "pomodoro",
  "subject_confidences": {
    "Mathematics": 8,
    "Physics": 7,
    "Computer Science": 9
  }
}
```

**Field Details:**
- `chronotype`: `"morning"`, `"evening"`, or `"neutral"`
- `study_style`: `"pomodoro"` or `"deep_work"`
- `subject_confidences`: Object with subject names as keys and confidence scores (1-10) as values

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
    study_style: 'pomodoro',
    subject_confidences: {
      'Math': 8,
      'Physics': 6,
      'Programming': 9
    }
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
    "color_code": "#FF5733",
    "is_archived": false
  },
  {
    "id": 2,
    "user_id": 1,
    "name": "Physics 101",
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
  "color_code": "#4CAF50",
  "is_archived": false
}
```

**Field Details:**
- `name`: Course name (must be unique per user)
- `color_code`: Hex color code for UI display
- `is_archived`: Whether the course is archived (default: false)

**Response:** `200 OK`
```json
{
  "id": 3,
  "user_id": 1,
  "name": "Data Structures",
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
- If date range provided: Returns tasks where `scheduled_start_time` is within range OR `deadline` is within range (for unscheduled tasks)
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
    "created_at": "2026-02-10T10:30:00",
    "course": {
      "id": 1,
      "name": "Calculus I",
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
Create a new task.

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
- The system checks for time slot collisions with other tasks and fixed schedule slots

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
  "created_at": "2026-02-10T11:00:00",
  "course": {
    "id": 1,
    "name": "Calculus I",
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
  "detail": "Time slot overlaps with existing task: 'Complete Assignment 3' (2026-02-14T14:00:00 - 2026-02-14T16:00:00)"
}
```

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
  "priority": "High"
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
  "scheduled_start_time": "2026-02-18T10:00:00",
  "scheduled_end_time": "2026-02-18T12:00:00",
  "estimated_duration_mins": 120,
  "course_id": 1,
  "created_at": "2026-02-10T11:00:00",
  "course": {
    "id": 1,
    "name": "Calculus I",
    "color_code": "#FF5733"
  }
}
```

**Error Responses:**
- `404 Not Found`: Task not found
- `409 Conflict`: Updated time slot overlaps with existing task or fixed schedule

**Note:** Collision checking is performed when scheduled times are modified.

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

---

## Schedule Endpoints

### 1. Get Fixed Schedule
Retrieve all fixed schedule slots for the current user.

**Endpoint:** `GET /schedule/fixed`

**Authentication:** Required (Bearer Token)

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "user_id": 1,
    "day_of_week": "Monday",
    "start_time": "09:00:00",
    "end_time": "11:00:00",
    "label": "Calculus Lecture",
    "is_google_event": false,
    "google_event_id": null
  },
  {
    "id": 2,
    "user_id": 1,
    "day_of_week": "Monday",
    "start_time": "14:00:00",
    "end_time": "16:00:00",
    "label": "Physics Lab",
    "is_google_event": false,
    "google_event_id": null
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
Add multiple fixed schedule slots at once.

**Endpoint:** `POST /schedule/fixed`

**Authentication:** Required (Bearer Token)

**Request Body:**
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
    "label": "Study Group",
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

**Note:** This endpoint performs bulk insert and does not replace existing slots. To update the schedule, delete existing slots first or implement a replace strategy on the frontend.

---

## Error Responses

### Standard HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request data or validation error
- `401 Unauthorized`: Missing or invalid authentication token
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate, time slot collision)
- `422 Unprocessable Entity`: Validation error (Pydantic)

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

**Validation Error:**
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

**Time Collision:**
```json
{
  "detail": "Time slot overlaps with existing task: 'Complete Assignment 3' (2026-02-14T14:00:00 - 2026-02-14T16:00:00)"
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

#### Study Style
```
"pomodoro" | "deep_work"
```

#### Day of Week
```
"Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday"
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

const loginResponse = await fetch('http://localhost:8000/api/v1/login/access-token', {
  method: 'POST',
  body: loginFormData
});

const { access_token } = await loginResponse.json();

// 3. Store token and use in subsequent requests
localStorage.setItem('token', access_token);

// 4. Use token in requests
const userResponse = await fetch('http://localhost:8000/api/v1/users/me', {
  headers: {
    'Authorization': `Bearer ${access_token}`
  }
});
```

### 2. Token Expiration

- Access tokens expire after 30 minutes
- Store the token expiration time when received
- Implement token refresh logic or re-login when expired
- Handle 401 responses by redirecting to login

### 3. Date/Time Handling

All datetime fields use ISO 8601 format:
```
"2026-02-14T14:00:00"
```

Convert JavaScript Date objects:
```javascript
const isoString = new Date().toISOString().slice(0, 19); // Remove milliseconds
```

### 4. Error Handling Best Practices

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

### 5. Onboarding Flow

```javascript
// 1. Check onboarding status
const status = await fetch('http://localhost:8000/api/v1/onboarding/status', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

if (!status.is_complete) {
  if (status.step === 'questionnaire') {
    // Show questionnaire form
  } else if (status.step === 'schedule') {
    // Show schedule setup
  }
}

// 2. Submit questionnaire
await fetch('http://localhost:8000/api/v1/onboarding/questionnaire', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    chronotype: 'morning',
    study_style: 'pomodoro',
    subject_confidences: { 'Math': 8 }
  })
});

// 3. Add fixed schedule
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
      label: 'Lecture',
      is_google_event: false
    }
  ])
});
```

### 6. Task Management Example

```javascript
// Create a course first
const course = await fetch('http://localhost:8000/api/v1/courses/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Calculus I',
    color_code: '#FF5733',
    is_archived: false
  })
}).then(r => r.json());

// Create a task linked to the course
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

// Update task status
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
```

---

## Interactive API Documentation

When the server is running, you can access interactive API documentation at:

- **Swagger UI:** http://localhost:8000/api/v1/docs
- **ReDoc:** http://localhost:8000/api/v1/redoc

These provide interactive interfaces to test all endpoints directly from your browser.

---

## Rate Limiting & Performance

- No rate limiting currently implemented
- Pagination available on list endpoints via `skip` and `limit` parameters
- Default limit: 100 items per request
- Recommend implementing frontend pagination for large datasets

---

## Support & Questions

For questions or issues with the API integration, please contact the backend team or refer to the source code in the `app/api/endpoints/` directory.

**Last Updated:** February 10, 2026  
**API Version:** 0.1.0
