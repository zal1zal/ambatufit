import React from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import IconNext from '../../assets/icon-next.svg';
import { tokens } from '../theme/tokens';
import { fontFamilies } from '../theme/fonts';

export function PrimaryButton({ title, onPress, disabled, loading, accessibilityLabel }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || title}
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        styles.primary,
        (disabled || loading) && { opacity: 0.55 },
        pressed && { transform: [{ scale: 0.99 }] },
      ]}
    >
      {loading ? (
        <ActivityIndicator color={tokens.color.textOnPrimary} />
      ) : (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Text style={styles.primaryText}>{title}</Text>
          <IconNext width={22} height={22} />
        </View>
      )}
    </Pressable>
  );
}
export function SecondaryButton({ title, onPress, style }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={[styles.secondary, style]}>
      <Text style={styles.secondaryText}>{title}</Text>
    </Pressable>
  );
}
export function TextField({
  label,
  value,
  onChangeText,
  placeholder,
  error,
  secureTextEntry,
  keyboardType,
  multiline,
  accessibilityLabel,
}) {
  return (
    <View style={{ gap: 8, marginBottom: 12 }}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        accessibilityLabel={accessibilityLabel || label}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={tokens.color.textMuted}
        secureTextEntry={secureTextEntry}
        keyboardType={keyboardType}
        multiline={multiline}
        textAlignVertical={multiline ? 'top' : 'center'}
        style={[
          styles.input,
          multiline && { height: 100, paddingTop: 12 },
          error && { borderColor: tokens.color.danger },
        ]}
      />
      {error ? (
        <Text accessibilityRole="alert" style={styles.error}>
          {error}
        </Text>
      ) : null}
    </View>
  );
}
export function Card({ children, dark = false, style }) {
  return <View style={[styles.card, dark && styles.dark, style]}>{children}</View>;
}
export function TechnicalLabel({ children, dark = false }) {
  return <Text style={[styles.tech, dark && { color: tokens.color.primary }]}>{children}</Text>;
}
export function PageTitle({ eyebrow, title, subtitle }) {
  return (
    <View style={{ marginBottom: 24 }}>
      {eyebrow ? <TechnicalLabel>{eyebrow}</TechnicalLabel> : null}
      <Text style={styles.title}>{title}</Text>
      {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
    </View>
  );
}
export function SafetyNotice({ level = 'urgent', message }) {
  const urgent = level === 'urgent';
  return (
    <View
      accessibilityRole="alert"
      style={[
        styles.notice,
        {
          backgroundColor: urgent ? tokens.color.dangerBackground : tokens.color.warningBackground,
          borderColor: urgent ? tokens.color.danger : tokens.color.warning,
        },
      ]}
    >
      <Text
        style={[styles.cardTitle, { color: urgent ? tokens.color.danger : tokens.color.warning }]}
      >
        {urgent ? 'PENTING: BANTUAN MEDIS' : 'PERLU PENINJAUAN'}
      </Text>
      <Text style={styles.body}>{message}</Text>
    </View>
  );
}
export function ServiceStatusNotice({ status, provider }) {
  return (
    <View style={styles.status}>
      <Text style={styles.tech}>
        {provider} /{' '}
        {status === 'available'
          ? 'TERSEDIA'
          : status === 'not_configured'
            ? 'BELUM TERHUBUNG'
            : 'TIDAK TERSEDIA'}
      </Text>
      <Text style={styles.bodySmall}>
        {status === 'available'
          ? 'Informasi dari layanan mitra tersedia.'
          : status === 'empty'
            ? 'Belum ada hasil yang sesuai.'
            : status === 'not_configured'
              ? 'Layanan mitra belum terhubung.'
              : 'Informasi dari layanan mitra sedang tidak tersedia. Silakan coba lagi.'}
      </Text>
    </View>
  );
}
export function ScreenState({ title, message, action, onPress }) {
  return (
    <Card>
      <TechnicalLabel>STATUS / INFORMASI</TechnicalLabel>
      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.body}>{message}</Text>
      {action ? <SecondaryButton title={action} onPress={onPress} /> : null}
    </Card>
  );
}
export function GuidanceCard({ item, status }) {
  return (
    <Card>
      <TechnicalLabel>
        {item?.source?.provider_id || item?.source_provider_id || 'PANDUAN PERSONAL'}
      </TechnicalLabel>
      <Text style={styles.cardTitle}>{item?.title || item?.name || 'Informasi kesehatan'}</Text>
      <Text style={styles.body}>
        {item?.description || item?.summary || 'Ikuti informasi umum sesuai profil kesehatan Anda.'}
      </Text>
      {status === 'needs_review' ? (
        <Text style={styles.error}>Perlu peninjauan profesional sebelum aktivitas fisik.</Text>
      ) : null}
    </Card>
  );
}
export function ProfessionalCard({ item, onPress }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress}>
      <Card>
        <TechnicalLabel>DIREKTORI / DATA DEMO</TechnicalLabel>
        <Text style={styles.cardTitle}>
          {item?.name || item?.display_name || 'Tenaga profesional'}
        </Text>
        <Text style={styles.body}>
          {item?.specialty ||
            item?.specialty_name ||
            'Informasi spesialisasi tersedia dari layanan.'}
        </Text>
        <Text style={styles.link}>Lihat jadwal ›</Text>
      </Card>
    </Pressable>
  );
}
export function ProviderAttribution({ children }) {
  return <Text style={styles.tech}>{children}</Text>;
}
export function ConsentToggle({ value, onChange }) {
  return (
    <Pressable
      accessibilityRole="checkbox"
      accessibilityState={{ checked: value }}
      onPress={() => onChange(!value)}
      style={styles.consent}
    >
      <View style={[styles.checkbox, value && { backgroundColor: tokens.color.primary }]}>
        <Text>{value ? '✓' : ''}</Text>
      </View>
      <Text style={[styles.body, { flex: 1 }]}>
        Bagikan ringkasan penilaian awal yang Anda pilih hanya kepada profesional dalam pemesanan
        ini. Persetujuan ini bersifat khusus dan dapat dicabut.
      </Text>
    </Pressable>
  );
}
export function BottomTabItem({ label, active, onPress, icon: Icon }) {
  return (
    <Pressable
      accessibilityRole="tab"
      accessibilityLabel={label}
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={{ flex: 1, minHeight: 76, alignItems: 'center', justifyContent: 'center', gap: 3 }}
    >
      <View
        style={{
          height: 3,
          width: 25,
          backgroundColor: active ? tokens.color.primary : tokens.color.surface,
        }}
      />
      <View
        style={{
          height: 34,
          width: 46,
          borderRadius: tokens.radius.sm,
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: active ? tokens.color.primary : tokens.color.surface,
        }}
      >
        {Icon ? <Icon width={24} height={24} /> : null}
      </View>
      <Text
        numberOfLines={1}
        style={{
          fontFamily: active ? fontFamilies.bodySemiBold : fontFamilies.bodyMedium,
          fontSize: 14,
          color: active ? tokens.color.text : tokens.color.textMuted,
        }}
      >
        {label}
      </Text>
    </Pressable>
  );
}
export function BackButton({ navigation }) {
  return (
    <SecondaryButton
      title="‹  Kembali"
      style={{ flex: 1, minHeight: 54 }}
      onPress={() => (navigation.canGoBack() ? navigation.goBack() : navigation.navigate('Home'))}
    />
  );
}
export function HomeButton({ navigation }) {
  return (
    <SecondaryButton
      title="⌂  Beranda"
      style={{ flex: 1, minHeight: 54 }}
      onPress={() => navigation.navigate('Home')}
    />
  );
}
export function EvidenceInput({ evidence, value, onChange, error }) {
  const options = evidence.options || evidence.allowed_values || [];
  const type = String(evidence.value_type || 'text').toLowerCase();
  const boolean = type.includes('bool');
  const label =
    evidence.label || evidence.question || evidence.question_text || 'Pertanyaan gejala';
  return (
    <Card style={error ? { borderColor: tokens.color.danger } : null}>
      <Text style={styles.cardTitle}>{label}</Text>
      {evidence.description ? <Text style={styles.bodySmall}>{evidence.description}</Text> : null}
      {boolean || options.length ? (
        <View style={{ gap: 8, marginTop: 8 }}>
          {(options.length ? options : [true, false]).map((opt, index) => {
            const v = typeof opt === 'object' ? (opt.value ?? opt.code) : opt;
            const choiceLabel =
              typeof opt === 'object'
                ? (opt.label ?? opt.name ?? `Pilihan ${index + 1}`)
                : typeof opt === 'boolean'
                  ? opt
                    ? 'Ya'
                    : 'Tidak'
                  : `Pilihan ${index + 1}`;
            return (
              <Pressable
                key={String(v)}
                onPress={() => onChange(v)}
                style={[styles.option, value === v && styles.selected]}
              >
                <Text style={styles.body}>{choiceLabel}</Text>
              </Pressable>
            );
          })}
        </View>
      ) : (
        <TextInput
          accessibilityLabel={label}
          value={value == null ? '' : String(value)}
          onChangeText={onChange}
          keyboardType={type.includes('number') ? 'numeric' : 'default'}
          style={styles.input}
        />
      )}
    </Card>
  );
}
export function ScreenShell({ children }) {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: tokens.color.background }}>
      <View style={{ height: 7, backgroundColor: tokens.color.primary }} />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.screen}>
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = {
  screen: { padding: 16, paddingTop: 0, paddingBottom: 36, gap: 12 },
  title: {
    fontFamily: fontFamilies.display,
    fontSize: 36,
    lineHeight: 40,
    color: tokens.color.text,
    marginTop: 8,
  },
  subtitle: {
    fontFamily: fontFamilies.body,
    fontSize: 14,
    lineHeight: 21,
    color: tokens.color.textMuted,
    marginTop: 8,
  },
  tech: {
    fontFamily: fontFamilies.mono,
    fontSize: 12,
    lineHeight: 17,
    letterSpacing: 0.5,
    color: tokens.color.accent,
  },
  label: { fontFamily: fontFamilies.body, fontSize: 14, lineHeight: 21, color: tokens.color.text },
  body: {
    fontFamily: fontFamilies.body,
    fontSize: 16,
    lineHeight: 24,
    color: tokens.color.text,
    marginTop: 6,
  },
  bodySmall: {
    fontFamily: fontFamilies.body,
    fontSize: 14,
    lineHeight: 21,
    color: tokens.color.textMuted,
    marginTop: 6,
  },
  cardTitle: {
    fontFamily: fontFamilies.bodySemiBold,
    fontSize: 18,
    lineHeight: 24,
    color: tokens.color.text,
    marginTop: 8,
  },
  card: {
    backgroundColor: tokens.color.surface,
    borderColor: tokens.color.border,
    borderWidth: 1,
    borderRadius: tokens.radius.md,
    padding: 16,
    gap: 6,
  },
  dark: { backgroundColor: tokens.color.surfaceDark, borderColor: tokens.color.surfaceDark },
  primary: {
    minHeight: 56,
    width: 310,
    maxWidth: '100%',
    backgroundColor: tokens.color.primary,
    borderRadius: tokens.radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    alignSelf: 'flex-start',
    marginTop: 8,
  },
  primaryText: {
    fontFamily: fontFamilies.bodySemiBold,
    fontSize: 17,
    lineHeight: 24,
    color: tokens.color.textOnPrimary,
  },
  secondary: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: tokens.color.text,
    borderRadius: tokens.radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 16,
    marginTop: 8,
  },
  secondaryText: { fontFamily: fontFamilies.bodySemiBold, fontSize: 16, color: tokens.color.text },
  input: {
    minHeight: 52,
    borderWidth: 1,
    borderColor: tokens.color.border,
    borderRadius: tokens.radius.sm,
    paddingHorizontal: 14,
    color: tokens.color.text,
    fontFamily: fontFamilies.body,
    fontSize: 16,
    backgroundColor: tokens.color.surface,
  },
  error: {
    color: tokens.color.danger,
    fontFamily: fontFamilies.body,
    fontSize: 14,
    lineHeight: 21,
    marginTop: 4,
  },
  notice: {
    borderLeftWidth: 5,
    borderWidth: 1,
    borderRadius: tokens.radius.md,
    padding: 16,
    gap: 6,
  },
  status: {
    padding: 12,
    borderLeftWidth: 3,
    borderColor: tokens.color.warning,
    backgroundColor: tokens.color.surface,
  },
  link: { fontFamily: fontFamilies.bodySemiBold, color: tokens.color.text, marginTop: 8 },
  option: {
    minHeight: 44,
    borderWidth: 1,
    borderColor: tokens.color.border,
    borderRadius: tokens.radius.sm,
    padding: 10,
    justifyContent: 'center',
  },
  selected: { borderColor: tokens.color.text, backgroundColor: tokens.color.warningBackground },
  consent: { flexDirection: 'row', gap: 12, alignItems: 'flex-start', padding: 12, minHeight: 60 },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 1,
    borderColor: tokens.color.text,
    alignItems: 'center',
    justifyContent: 'center',
  },
};

export const uiStyles = styles;
