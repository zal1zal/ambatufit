# User flows

1. Restore SecureStore token, validate `/auth/me`; otherwise show Login. Successful login stores only the returned bearer token in SecureStore.
2. Home → symptom assessment: load actual evidence metadata, answer typed fields, validate, submit once, then retrieve the result by ID. Render backend safety status first and always show the non-diagnostic disclaimer.
3. Home → guidance/progress/profile: guidance content comes from the core service and stays separate from partner status; check-ins save and reload from monitoring API.
4. Guidance → nutrition or gyms: call integration API and attribute partner data from the response.
5. Home/profile → professionals → returned slot → booking. Consent starts unchecked and is scoped to selected assessment, professional, booking; revoke from bookings.
