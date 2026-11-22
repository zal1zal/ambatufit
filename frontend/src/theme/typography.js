import { fontFamilies } from './fonts';

export const typography = Object.freeze({
  'Type/Display': {
    fontFamily: fontFamilies.display,
    fontSize: 48,
    lineHeight: 50,
    letterSpacing: -0.5,
  },
  'Type/PageTitle': {
    fontFamily: fontFamilies.display,
    fontSize: 36,
    lineHeight: 40,
    letterSpacing: 0,
  },
  'Type/SectionTitle': {
    fontFamily: fontFamilies.displaySemiBold,
    fontSize: 28,
    lineHeight: 32,
    letterSpacing: 0,
  },
  'Type/CardTitle': {
    fontFamily: fontFamilies.bodySemiBold,
    fontSize: 18,
    lineHeight: 24,
    letterSpacing: 0,
  },
  'Type/Body': {
    fontFamily: fontFamilies.body,
    fontSize: 16,
    lineHeight: 24,
    letterSpacing: 0,
  },
  'Type/BodySmall': {
    fontFamily: fontFamilies.body,
    fontSize: 14,
    lineHeight: 21,
    letterSpacing: 0,
  },
  'Type/Button': {
    fontFamily: fontFamilies.bodySemiBold,
    fontSize: 16,
    lineHeight: 22,
    letterSpacing: 0.1,
  },
  'Type/NavLabel': {
    fontFamily: fontFamilies.bodyMedium,
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.1,
  },
  'Type/TechnicalLabel': {
    fontFamily: fontFamilies.mono,
    fontSize: 12,
    lineHeight: 17,
    letterSpacing: 0.5,
  },
  'Type/MicroLabel': {
    fontFamily: fontFamilies.mono,
    fontSize: 11,
    lineHeight: 16,
    letterSpacing: 0.3,
  },
  'Type/Metric': {
    fontFamily: fontFamilies.display,
    fontSize: 38,
    lineHeight: 40,
    letterSpacing: 0,
  },
});

export default typography;
