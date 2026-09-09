# MEA Thailand Grid Tariffs

Custom Component for Home Assistant to parse real-time electricity tariff rates from the Metropolitan Electricity Authority (MEA) official website.

> **Disclaimer:** This is an unofficial, community-developed integration and is not affiliated with or endorsed by the Metropolitan Electricity Authority (MEA).

---

## Features

* **Complete MEA Residential Type 1 (Household) Tariffs:**
  * **Rate 1.1:** Household consumption < 150 kWh (Tier 1–5 breakdown)
  * **Rate 1.2:** Household consumption > 150 kWh (Tier 1–3 breakdown)
  * **Rate 1.3.1:** TOU Voltage 12–24 kV (On-Peak / Off-Peak)
  * **Rate 1.3.2:** TOU Voltage < 12 kV (On-Peak / Off-Peak)
* **Automatic Ft Tracking:** Fetches current Ft values with satang-per-unit state attributes.
* **Service Charge Tracking:** Dedicated monthly base service charge entity per tariff selection.
* **TOU Status Tracking:** Status sensor indicating current On-Peak / Off-Peak period (accounting for weekends and public holidays, customizable via `holidays.txt`).
* **UI Config Flow:** Easy configuration directly through the Home Assistant interface.

---

## Sensor Entities

The entities generated depend on the sub-tariff category selected during integration setup. All entity IDs use the base prefix `sensor.mea_thailand_grid_tariff_residential_1_`.

### Overview

| Sensor Category | Entity ID Pattern | Unit | Description |
| :--- | :--- | :---: | :--- |
| **Ft Rate** | `sensor.mea_thailand_grid_tariff_residential_1_<slug>_ft_rate` | `THB/kWh` | Global current Ft variable rate |
| **On Peak Rate** | `sensor.mea_thailand_grid_tariff_residential_1_<slug>_on_peak` | `THB/kWh` | TOU peak electricity rate |
| **Off Peak Rate** | `sensor.mea_thailand_grid_tariff_residential_1_<slug>_off_peak` | `THB/kWh` | TOU off-peak electricity rate |
| **TOU Status** | `sensor.mea_thailand_grid_tariff_residential_1_<slug>_tou_time_status` | String | Current TOU period status |
| **Tier Rate** | `sensor.mea_thailand_grid_tariff_residential_1_<slug>_tier<N>_<range>` | `THB/kWh` | Step/tiered consumption rate |
| **Service Charge** | `sensor.mea_thailand_grid_tariff_residential_1_<slug>_service_charge` | `THB` | Base monthly service fee |

---

### Generated Entities by Selected Sub-Tariff

<details>
<summary><b>Type 1.1 — Household ≤ 150 kWh (le150)</b></summary>

* `sensor.mea_thailand_grid_tariff_residential_1_type_1_1_below_150_tier1_1_15`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_1_below_150_tier2_16_25`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_1_below_150_tier3_26_200`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_1_below_150_tier4_201_400`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_1_below_150_tier5_401_onward`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_1_below_150_service_charge`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_1_below_150_ft_rate`

</details>

<details>
<summary><b>Type 1.2 — Household > 150 kWh (gt150)</b></summary>

* `sensor.mea_thailand_grid_tariff_residential_1_type_1_2_greater_150_tier1_1_200`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_2_greater_150_tier2_201_400`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_2_greater_150_tier3_401_onward`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_2_greater_150_service_charge`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_2_greater_150_ft_rate`

</details>

<details>
<summary><b>Type 1.3.1 — TOU Voltage 12–24 kV (tou_131)</b></summary>

* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_1_tou_12_24_on_peak`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_1_tou_12_24_off_peak`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_1_tou_12_24_tou_time_status`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_1_tou_12_24_service_charge`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_1_tou_12_24_ft_rate`

</details>

<details>
<summary><b>Type 1.3.2 — TOU Voltage < 12 kV (tou_132)</b></summary>

* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_2_tou_under_12_on_peak`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_2_tou_under_12_off_peak`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_2_tou_under_12_tou_time_status`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_2_tou_under_12_service_charge`
* `sensor.mea_thailand_grid_tariff_residential_1_type_1_3_2_tou_under_12_ft_rate`

</details>

---

## Installation

### Method 1: HACS (Custom Repository)
1. Open **HACS** in Home Assistant.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Add Repository URL: `https://github.com/terngz/mea_thailand_grid_tariffs`
4. Select **Integration** as the category and click **Add**.
5. Find **MEA Thailand Grid Tariffs** and click **Download**.
6. Restart Home Assistant.

### Method 2: Manual Installation
1. Download the latest release from the Releases page.
2. Copy the `custom_components/mea_thailand_grid_tariffs` directory to your Home Assistant `/config/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

1. Navigate to **Settings** -> **Devices & Services**.
2. Click **Add Integration**.
3. Search for `MEA Thailand Grid Tariffs`.
4. Select your household tariff type (e.g. Type 1.1 < 150 Units or Type 1.2 > 150 Units)
5. Click **Submit**.

---

## Development & Credits

* Developed by [@terngz](https://github.com/terngz)
* Data Source: [Metropolitan Electricity Authority (MEA)](https://www.mea.or.th/)

---

## Acknowledgements & Inspiration

* **Project Inspiration:** This project was inspired by [Manneaber/hacs-mea-electricity-tariffs](https://github.com/Manneaber/hacs-mea-electricity-tariffs/). As the original repository is not update, this custom component was built from scratch to provide a modern, updated, and tailored solution.

* **Development Approach:** No legacy code from the original repository was used. The codebase was completely rewritten from the ground up using **AI Vibe Coding** (assisted by Claude & Gemini) to fit a new architecture, custom entity structure, and personal preferences.