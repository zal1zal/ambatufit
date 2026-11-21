import React, { useState } from 'react';
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
export function SecondaryButton({ title, onPress, style, disabled }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={title}
      disabled={disabled}
      onPress={onPress}
      style={[styles.secondary, disabled && { opacity: 0.45 }, style]}
    >
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
  dark = false,
}) {
  return (
    <View style={{ gap: 8, marginBottom: 12 }}>
      <Text style={[styles.label, dark && { color: tokens.color.textOnDark }]}>{label}</Text>
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
        {urgent ? 'PENTING: BANTUAN MEDIS' : 'DISCLAIMER'}
      </Text>
      <Text style={styles.body}>{message}</Text>
    </View>
  );
}

const stripInternalRefs = (raw) =>
  String(raw || '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\[(?:Sumber|Ref|SRC|E\d|D\d|M\d)[^\]]*\]/gi, '')
    .replace(/\s{2,}/g, ' ')
    .trim();

export function FormattedText({ text, dark = false }) {
  const color = dark ? tokens.color.textOnDark : tokens.color.text;
  const muted = dark ? tokens.color.mutedOnDark : tokens.color.textMuted;
  const lines = String(text || '').split('\n');
  return (
    <View style={{ gap: 6, marginTop: 4 }}>
      {lines.map((rawLine, idx) => {
        const line = stripInternalRefs(rawLine);
        if (!line) return <View key={idx} style={{ height: 4 }} />;
        if (line.startsWith('### ')) {
          return (
            <Text
              key={idx}
              style={{
                fontFamily: fontFamilies.bodySemiBold,
                fontSize: 18,
                lineHeight: 25,
                color: dark ? tokens.color.primary : tokens.color.text,
                marginTop: idx > 0 ? 8 : 0,
              }}
            >
              {line.slice(4)}
            </Text>
          );
        }
        if (line.startsWith('• ') || line.startsWith('- ')) {
          return (
            <Text
              key={idx}
              style={{
                fontFamily: fontFamilies.body,
                fontSize: 15,
                lineHeight: 22,
                color,
                paddingLeft: 8,
              }}
            >
              • {line.slice(2).trim()}
            </Text>
          );
        }
        return (
          <Text
            key={idx}
            style={{ fontFamily: fontFamilies.body, fontSize: 15, lineHeight: 22, color: dark ? muted : color }}
          >
            {line}
          </Text>
        );
      })}
    </View>
  );
}

export function SimpleTable({ headers = [], rows = [] }) {
  if (!headers.length || !rows.length) return null;
  return (
    <View
      style={{
        borderWidth: 1,
        borderColor: tokens.color.border,
        borderRadius: tokens.radius.sm,
        overflow: 'hidden',
        marginTop: 6,
      }}
    >
      <View
        style={{
          flexDirection: 'row',
          backgroundColor: tokens.color.warningBackground,
          borderBottomWidth: 1,
          borderColor: tokens.color.border,
        }}
      >
        {headers.map((h, i) => (
          <Text
            key={i}
            style={{
              flex: 1,
              padding: 8,
              fontFamily: fontFamilies.bodySemiBold,
              fontSize: 13,
              color: tokens.color.text,
            }}
          >
            {h}
          </Text>
        ))}
      </View>
      {rows.map((row, rIdx) => (
        <View
          key={rIdx}
          style={{
            flexDirection: 'row',
            backgroundColor: rIdx % 2 === 0 ? tokens.color.surface : tokens.color.background,
            borderBottomWidth: rIdx < rows.length - 1 ? 1 : 0,
            borderColor: tokens.color.border,
          }}
        >
          {row.map((cell, cIdx) => (
            <Text
              key={cIdx}
              style={{
                flex: 1,
                padding: 8,
                fontFamily: cIdx === 0 ? fontFamilies.bodySemiBold : fontFamilies.body,
                fontSize: 13,
                lineHeight: 19,
                color: tokens.color.text,
              }}
            >
              {String(cell ?? '—')}
            </Text>
          ))}
        </View>
      ))}
    </View>
  );
}

export function cleanWebCitations(citations) {
  return (citations || []).filter((c) => {
    const url = String(c?.url || '').trim();
    if (!url.startsWith('https://')) return false;
    if (url.includes('example.invalid')) return false;
    // Exclude static synthetic benchmark DOI or raw fallback links from visual "Referensi Internet"
    if (url.includes('doi.org/10.6084/m9.figshare.22687585')) return false;
    return true;
  });
}

export function formatIndonesianDate(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const months = [
    'Januari',
    'Februari',
    'Maret',
    'April',
    'Mei',
    'Juni',
    'Juli',
    'Agustus',
    'September',
    'Oktober',
    'November',
    'Desember',
  ];
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}, pukul ${hh}.${mm}`;
}

export function formatSlotDateParts(startsAt, endsAt) {
  const days = ['MINGGU', 'SENIN', 'SELASA', 'RABU', 'KAMIS', 'JUMAT', 'SABTU'];
  const shortMonths = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
  const start = new Date(startsAt);
  if (Number.isNaN(start.getTime())) {
    return { day: 'JADWAL', date: String(startsAt || '—'), time: '' };
  }
  const sh = String(start.getHours()).padStart(2, '0');
  const sm = String(start.getMinutes()).padStart(2, '0');
  let timeRange = `${sh}.${sm} WIB`;
  if (endsAt) {
    const end = new Date(endsAt);
    if (!Number.isNaN(end.getTime())) {
      const eh = String(end.getHours()).padStart(2, '0');
      const em = String(end.getMinutes()).padStart(2, '0');
      timeRange = `${sh}.${sm} – ${eh}.${em} WIB`;
    }
  }
  return {
    day: days[start.getDay()],
    date: `${start.getDate()} ${shortMonths[start.getMonth()]} ${start.getFullYear()}`,
    time: timeRange,
  };
}

let ExpoCameraView = null;
let useExpoCameraPermissions = null;
try {
  const expoCam = require('expo-camera');
  ExpoCameraView = expoCam?.CameraView || null;
  useExpoCameraPermissions = expoCam?.useCameraPermissions || null;
} catch {
  ExpoCameraView = null;
  useExpoCameraPermissions = null;
}

export function CameraBarcodeScanner({ onScanned }) {
  const [scanned, setScanned] = useState(false);
  const permHookRes = typeof useExpoCameraPermissions === 'function' ? useExpoCameraPermissions() : null;
  const permission = permHookRes?.[0] || null;
  const requestPermission = permHookRes?.[1] || null;

  if (!ExpoCameraView || !useExpoCameraPermissions || Platform.OS === 'web') {
    return (
      <View
        style={{
          padding: 12,
          borderRadius: tokens.radius.sm,
          borderWidth: 1,
          borderColor: tokens.color.border,
          backgroundColor: 'rgba(255,255,255,0.06)',
          gap: 6,
        }}
      >
        <Text style={{ fontFamily: fontFamilies.bodySemiBold, fontSize: 14, color: tokens.color.textOnDark }}>
          Pemindai kamera aktif di perangkat Android / iOS (Expo Go)
        </Text>
        <Text style={{ fontFamily: fontFamilies.body, fontSize: 13, color: tokens.color.mutedOnDark }}>
          Pada peramban web atau mode pengujian, silakan ketik angka barcode (EAN-13) / Nomor Izin Edar di kolom bawah.
        </Text>
      </View>
    );
  }

  if (!permission) {
    return <ActivityIndicator color={tokens.color.primary} style={{ marginVertical: 12 }} />;
  }

  if (!permission.granted) {
    return (
      <View
        style={{
          padding: 14,
          borderRadius: tokens.radius.sm,
          borderWidth: 1,
          borderColor: tokens.color.primary,
          backgroundColor: 'rgba(255,255,255,0.06)',
          gap: 10,
        }}
      >
        <Text style={{ fontFamily: fontFamilies.bodySemiBold, fontSize: 14, color: tokens.color.textOnDark }}>
          Izin Kamera Diperlukan
        </Text>
        <Text style={{ fontFamily: fontFamilies.body, fontSize: 13, color: tokens.color.mutedOnDark }}>
          Izinkan akses kamera agar Anda dapat mengarahkan ponsel ke barcode (EAN-13) pada kemasan obat.
        </Text>
        <PrimaryButton title="Buka Izin Kamera" onPress={() => requestPermission && requestPermission()} />
      </View>
    );
  }

  return (
    <View style={{ gap: 8 }}>
      <View
        style={{
          height: 230,
          borderRadius: tokens.radius.md,
          overflow: 'hidden',
          borderWidth: 2,
          borderColor: tokens.color.primary,
          backgroundColor: '#000',
          position: 'relative',
        }}
      >
        <ExpoCameraView
          style={{ flex: 1 }}
          facing="back"
          barcodeScannerSettings={{
            barcodeTypes: ['ean13', 'ean8', 'upc_a', 'upc_e', 'code128', 'qr'],
          }}
          onBarcodeScanned={
            scanned
              ? undefined
              : ({ data }) => {
                  if (!data) return;
                  setScanned(true);
                  onScanned?.(String(data).trim());
                }
          }
        />
        <View
          pointerEvents="none"
          style={{
            position: 'absolute',
            top: '22%',
            left: '12%',
            right: '12%',
            bottom: '22%',
            borderWidth: 2,
            borderColor: tokens.color.primary,
            borderRadius: tokens.radius.sm,
          }}
        />
      </View>
      <Text style={{ fontFamily: fontFamilies.body, fontSize: 13, color: tokens.color.mutedOnDark }}>
        {scanned
          ? 'Barcode berhasil dipindai.'
          : 'Arahkan kotak bidik kamera tepat ke barcode kemasan obat.'}
      </Text>
      {scanned && (
        <SecondaryButton
          title="Pindai Ulang"
          onPress={() => setScanned(false)}
          style={{ backgroundColor: tokens.color.surface }}
        />
      )}
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
      ) : status === 'unavailable' ? (
        <Text style={styles.bodySmall}>Panduan ini sedang tidak tersedia.</Text>
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
  const multi = type === 'multichoice';
  const label = evidence.question_id || evidence.label_id || 'Pertanyaan gejala';
  const [draftText, setDraftText] = useState('');
  const [pickedCodes, setPickedCodes] = useState(() =>
    Array.isArray(value) ? value : value != null && value !== '' ? [value] : [],
  );

  const isNumericScale =
    options.length > 5 &&
    options.every((opt) => typeof (typeof opt === 'object' ? opt.value : opt) === 'number');

  const labelForVal = (val) => {
    const match = options.find((o) => (typeof o === 'object' ? o.value : o) === val);
    if (!match) return String(val);
    return typeof match === 'object' ? (match.label_id ?? String(val)) : String(match);
  };

  if (boolean || (options.length > 0 && options.length <= 5)) {
    return (
      <Card style={error ? { borderColor: tokens.color.danger } : null}>
        <Text style={styles.cardTitle}>{label}</Text>
        {evidence.description ? <Text style={styles.bodySmall}>{evidence.description}</Text> : null}
        <View style={{ gap: 8, marginTop: 8 }}>
          {(options.length ? options : [true, false]).map((opt, index) => {
            const v = typeof opt === 'object' ? (opt.value ?? opt.code) : opt;
            const choiceLabel =
              typeof opt === 'object'
                ? (opt.label_id ?? opt.label ?? opt.name ?? `Pilihan ${index + 1}`)
                : typeof opt === 'boolean'
                  ? opt
                    ? 'Ya'
                    : 'Tidak'
                  : `Pilihan ${index + 1}`;
            const selected = multi ? Array.isArray(value) && value.includes(v) : value === v;
            return (
              <Pressable
                key={String(v)}
                accessibilityRole={multi ? 'checkbox' : 'radio'}
                accessibilityState={{ checked: selected }}
                onPress={() =>
                  onChange(
                    multi
                      ? selected
                        ? value.filter((x) => x !== v)
                        : [...(Array.isArray(value) ? value : []), v]
                      : v,
                  )
                }
                style={[styles.option, selected && styles.selected]}
              >
                <Text style={styles.body}>{choiceLabel}</Text>
              </Pressable>
            );
          })}
        </View>
      </Card>
    );
  }

  if (isNumericScale) {
    return (
      <Card style={error ? { borderColor: tokens.color.danger } : null}>
        <Text style={styles.cardTitle}>{label}</Text>
        <Text style={styles.bodySmall}>Ketik angka 0 sampai 10 atau pilih skala cepat:</Text>
        <TextInput
          accessibilityLabel={label}
          value={value == null ? '' : String(value)}
          onChangeText={(txt) => {
            const cleaned = txt.replace(/[^0-9]/g, '');
            if (!cleaned) onChange(undefined);
            else {
              const num = Math.min(10, Math.max(0, Number(cleaned)));
              onChange(num);
            }
          }}
          keyboardType="numeric"
          placeholder="0 - 10"
          style={styles.input}
        />
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
          {options.map((opt) => {
            const v = typeof opt === 'object' ? opt.value : opt;
            const selected = value === v;
            return (
              <Pressable
                key={String(v)}
                onPress={() => onChange(v)}
                style={{
                  minWidth: 38,
                  paddingVertical: 8,
                  paddingHorizontal: 10,
                  borderRadius: tokens.radius.sm,
                  borderWidth: 1,
                  borderColor: selected ? tokens.color.text : tokens.color.border,
                  backgroundColor: selected ? tokens.color.primary : tokens.color.surface,
                  alignItems: 'center',
                }}
              >
                <Text style={styles.bodySmall}>{String(v)}</Text>
              </Pressable>
            );
          })}
        </View>
      </Card>
    );
  }

  if (options.length > 5) {
    const q = draftText.trim().toLowerCase();
    const suggestions = q
      ? options
          .filter((opt) => {
            const lbl = (typeof opt === 'object' ? opt.label_id : String(opt)).toLowerCase();
            return lbl.includes(q);
          })
          .slice(0, 5)
      : [];

    const addChoice = (val) => {
      if (multi) {
        const next = pickedCodes.includes(val) ? pickedCodes : [...pickedCodes, val];
        setPickedCodes(next);
        setDraftText('');
        onChange(next);
      } else {
        setPickedCodes([val]);
        setDraftText(labelForVal(val));
        onChange(val);
      }
    };

    const removeChoice = (val) => {
      const next = pickedCodes.filter((x) => x !== val);
      setPickedCodes(next);
      onChange(multi ? (next.length ? next : undefined) : undefined);
    };

    return (
      <Card style={error ? { borderColor: tokens.color.danger } : null}>
        <Text style={styles.cardTitle}>{label}</Text>
        <Text style={styles.bodySmall}>
          Tulis jawaban Anda langsung di kolom ini (tersedia saran otomatis saat mengetik).
        </Text>
        <TextInput
          accessibilityLabel={label}
          value={draftText}
          onChangeText={(txt) => {
            setDraftText(txt);
            const trimmed = txt.trim();
            if (multi) {
              const combined = trimmed ? [...pickedCodes, trimmed] : pickedCodes;
              onChange(combined.length ? combined : undefined);
            } else {
              onChange(trimmed || undefined);
            }
          }}
          placeholder="Contoh: ulu hati, kepala, kaki kanan, nyeri tajam..."
          style={styles.input}
        />
        {pickedCodes.length > 0 && (
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6 }}>
            {pickedCodes.map((code) => (
              <Pressable
                key={String(code)}
                onPress={() => removeChoice(code)}
                style={[styles.option, styles.selected, { minHeight: 36, paddingVertical: 6, paddingHorizontal: 10 }]}
              >
                <Text style={styles.bodySmall}>{labelForVal(code)} ×</Text>
              </Pressable>
            ))}
          </View>
        )}
        {suggestions.length > 0 && (
          <View style={{ gap: 6, marginTop: 4 }}>
            <Text style={styles.bodySmall}>Pilih saran yang sesuai:</Text>
            {suggestions.map((opt) => {
              const v = typeof opt === 'object' ? (opt.value ?? opt.code) : opt;
              const lbl = typeof opt === 'object' ? (opt.label_id ?? String(v)) : String(opt);
              return (
                <Pressable
                  key={String(v)}
                  onPress={() => addChoice(v)}
                  style={[styles.option, { minHeight: 40, paddingVertical: 8 }]}
                >
                  <Text style={styles.bodySmall}>+ {lbl}</Text>
                </Pressable>
              );
            })}
          </View>
        )}
      </Card>
    );
  }

  return (
    <Card style={error ? { borderColor: tokens.color.danger } : null}>
      <Text style={styles.cardTitle}>{label}</Text>
      {evidence.description ? <Text style={styles.bodySmall}>{evidence.description}</Text> : null}
      <TextInput
        accessibilityLabel={label}
        value={value == null ? '' : String(value)}
        onChangeText={onChange}
        keyboardType={type.includes('number') ? 'numeric' : 'default'}
        style={styles.input}
      />
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
