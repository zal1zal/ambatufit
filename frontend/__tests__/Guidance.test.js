import { userMessage } from '../src/services/apiErrors';
test('partner unconfigured and upstream failure are presented honestly', () => {
  expect(userMessage({ code: 'not_configured' })).toMatch(/belum terhubung/);
  expect(userMessage({ status: 503 })).toMatch(/kendala jaringan/);
});
