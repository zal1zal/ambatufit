import { userMessage } from '../src/services/apiErrors';
test('booking collision requires choosing a different slot', () =>
  expect(userMessage({ status: 409 })).toMatch(/Pilih waktu lain/));
