// Lightweight runtime mapper that converts legacy snake_case settings to
// the new camelCase structure the frontend types expect.

/**
 * @typedef {any} SettingsShape
 */

/**
 * @param {SettingsShape} raw
 * @returns {SettingsShape}
 */
export function normalizeSettings(raw) {
  if (!raw || typeof raw !== 'object') return raw;

  const settings = { ...raw };

  // Helper to copy a nested snake_case key to camelCase if present
  /**
   * Copy a nested property from the original payload into the normalized shape
   * if present. Uses dot-separated paths.
   * @param {string} fromPath
   * @param {string} toPath
   */
  const copy = (fromPath, toPath) => {
    const fromParts = fromPath.split('.');
    let src = raw;
    for (const p of fromParts) {
      if (src && typeof src === 'object' && p in src) src = src[p];
      else {
        src = undefined;
        break;
      }
    }
    if (src !== undefined) {
      const toParts = toPath.split('.');
      let dest = settings;
      for (let i = 0; i < toParts.length - 1; i++) {
        const k = toParts[i];
        if (!(k in dest) || typeof dest[k] !== 'object') dest[k] = {};
        dest = dest[k];
      }
      dest[toParts[toParts.length - 1]] = src;
    }
  };

  // Common mappings observed in the codebase
  // GPIO
  copy('gpio.data_pin', 'gpio_pin');
  copy('gpio.data_pin', 'gpio.gpio_pin');

  // LED settings
  copy('led.led_count', 'led_count');
  copy('led.led_count', 'led.led_count');
  copy('led.max_led_count', 'led.max_led_count');
  copy('led.led_orientation', 'led.led_orientation');
  copy('led.led_type', 'led.led_type');
  copy('led.data_pin', 'gpio.data_pin');
  copy('led.power_supply_voltage', 'led.power_supply_voltage');
  copy('led.color_profile', 'led.color_profile');
  copy('led.performance_mode', 'led.performance_mode');
  copy('led.white_balance', 'led.white_balance');
  copy('led.update_rate', 'led.update_rate');
  copy('led.power_limiting_enabled', 'led.power_limiting_enabled');
  copy('led.max_power_watts', 'led.max_power_watts');
  copy('led.thermal_protection_enabled', 'led.thermal_protection_enabled');
  copy('led.max_temperature_celsius', 'led.max_temperature_celsius');

  // Map advanced settings into shape expected by LED UI components
  copy('led.gamma_correction', 'led.advancedSettings.gamma');
  copy('led.gamma', 'led.advancedSettings.gamma');
  copy('led.color_temperature', 'led.advancedSettings.colorTemp');
  copy('led.color_temp', 'led.advancedSettings.colorTemp');
  copy('led.dither_enabled', 'led.advancedSettings.dither');
  copy('led.update_rate', 'led.advancedSettings.updateRate');
  copy('led.power_limiting_enabled', 'led.advancedSettings.powerLimiting');
  copy('led.max_power_watts', 'led.advancedSettings.maxPowerWatts');
  copy('led.thermal_protection_enabled', 'led.advancedSettings.thermalProtection');
  copy('led.max_temperature_celsius', 'led.advancedSettings.maxTemp');
  copy('led.white_balance', 'led.advancedSettings.whiteBalance');
  // Thermal / power helper fields
  copy('led.ambient_temp', 'led.advancedSettings.ambientTemp');
  copy('led.thermal_resistance', 'led.advancedSettings.thermalResistance');

  // Top-level convenience fields used by some components
  copy('led.power_supply_voltage', 'led.powerSupplyVoltage');
  copy('led.power_supply_current', 'led.powerSupplyCurrent');
  copy('led.brightness', 'led.brightness');
  copy('brightness', 'led.brightness');
  copy('led.led_type', 'led.ledType');
  copy('led.led_count', 'led.ledCount');
  copy('led.max_led_count', 'led.maxLedCount');

  // Piano settings
  copy('piano.size', 'piano.size');
  copy('piano.keys', 'piano.keys');
  copy('piano.octaves', 'piano.octaves');
  copy('piano.start_note', 'piano.start_note');
  copy('piano.end_note', 'piano.end_note');
  copy('piano.key_mapping_mode', 'piano.key_mapping_mode');

  // Backwards-compat top-level keys that older code referenced
  if ('led_count' in raw && !('led' in settings)) settings.led_count = raw.led_count;
  if ('gpio_pin' in raw && !('gpio' in settings)) settings.gpio_pin = raw.gpio_pin;

  // Normalize brightness: some places expect 0.0-1.0, others 0-100 — leave as-is

  return settings;
}
