# MVCA Flood & Low Water

Home Assistant custom integration for [Mississippi Valley Conservation Authority](https://mvc.on.ca/) flood and low-water status.

It polls the [MVCA water management dashboard](https://mvc.on.ca/engineering/water-management-dashboard/) and creates sensors for:

- Mississippi River
- Carp River
- Lower Ottawa

Each river has a **flood status** sensor and a **low water status** sensor.

## Installation

### HACS

1. In HACS, add this repository as a **custom repository** of type **Integration**:
   `https://github.com/dvinceXX/home-assistant-mvca-flood`
2. Search for **MVCA Flood & Low Water** and download it.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**.
5. Search for **MVCA Flood & Low Water**.

### Manual

Copy `custom_components/mvca_flood` into your Home Assistant `config/custom_components/` directory, then restart Home Assistant and add the integration as above.

## Configuration

Setup asks for the dashboard poll interval (5–1440 minutes, default 30).

After setup, change that interval from the integration’s **Configure** options. Home Assistant reloads the integration when you save.

Only one instance of this integration is supported.

## Sensors

All sensors are attached to a single device: **MVCA Flood & Low Water**.

| Sensor | Description |
| --- | --- |
| Mississippi River Flood Status | Flood messaging for the Mississippi River |
| Carp River Flood Status | Flood messaging for the Carp River |
| Lower Ottawa Flood Status | Flood messaging for the Lower Ottawa |
| Mississippi River Low Water Status | Low-water messaging for the Mississippi River |
| Carp River Low Water Status | Low-water messaging for the Carp River |
| Lower Ottawa Low Water Status | Low-water messaging for the Lower Ottawa |

Typical flood values include `Normal`, watershed condition statements, `Flood Watch`, and `Flood Warning`. Typical low-water values include `Normal`, `Level I`, `Level II`, and `Level III`. The integration stores the text published on the dashboard.

Each sensor includes a `source` attribute pointing at the MVCA dashboard.

## Data source

Status is scraped from the public MVCA dashboard. If MVCA changes the page layout, parsing can fail until the integration is updated.

## Development

GitHub Actions run [HACS validation](https://github.com/hacs/action) and [Hassfest](https://github.com/home-assistant/actions) on push and pull request.
