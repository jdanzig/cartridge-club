# Product model

Three entities. Everything else hangs off them.

## 1. `console` metaobject

Type handle: `console`. ~15 entries seeded from
[`fixtures/consoles.json`](../fixtures/consoles.json).

| Field | Type | Notes |
| --- | --- | --- |
| `name` | single_line_text_field | "Nintendo 64" |
| `manufacturer` | single_line_text_field | "Nintendo" |
| `release_year` | number_integer | 1996 |
| `region_codes` | list.single_line_text_field | `["NTSC-U","NTSC-J","PAL"]` |
| `controller_port_spec` | single_line_text_field | `n64_controller_port` |
| `cartridge_format` | single_line_text_field | `n64` |
| `av_output_types` | list.single_line_text_field | `["composite","s_video"]` |
| `generation` | single_line_text_field | `fifth_gen` |

Modeled as a metaobject (not just tags) so the embedded app and Functions
can both read it as a first-class entity.

## 2. Accessory (Shopify Product + metafields)

~30 products seeded from
[`fixtures/accessories.json`](../fixtures/accessories.json). Each carries
this metafield bundle under namespace `custom`:

| Metafield | Type | Purpose |
| --- | --- | --- |
| `compatible_consoles` | `list.metaobject_reference` (→ `console`) | Which consoles this works with. |
| `connector_type` | single_line_text_field | Mechanical port type. |
| `input_connector` | single_line_text_field | For cables / adapters. |
| `output_connector` | single_line_text_field | For cables / adapters. |
| `supported_resolutions` | list.single_line_text_field | `["240p","480i"]` etc. |
| `requires_accessory` | list.single_line_text_field | Other product handles that must be in cart. |
| `incompatible_with` | list.single_line_text_field | Hard incompatibilities. |
| `region` | single_line_text_field | `ntsc` / `pal` / `worldwide`. |
| `console_generation` | single_line_text_field | `fourth_gen`, `fifth_gen`… |
| `bundle_type` | single_line_text_field | `starter_kit` for bundle products. |
| `bundle_components` | list.single_line_text_field | Child handles, only for bundles. |
| `accessory_kind` | single_line_text_field | `controller`, `cable`, `av`, `maintenance`, etc. |
| `warning` | multi_line_text_field | Free-text caveat shown by the theme + finder. |
| `audit_status` | single_line_text_field | Written by webhook handler. |

## 3. `compatibility_rule` metaobject

Type handle: `compatibility_rule`. Captures non-obvious cases that don't
fit a per-product metafield. ~12 entries seeded from
[`fixtures/compatibility-rules.json`](../fixtures/compatibility-rules.json).

| Field | Type | Purpose |
| --- | --- | --- |
| `source_console` | metaobject_reference → `console` | "Coming from a…" |
| `target_console` | metaobject_reference → `console` | "Going to a…" |
| `accessory_kind` | single_line_text_field | Scopes the rule to a kind of accessory. |
| `status` | single_line_text_field | `works` / `works_with_caveats` / `requires_adapter` / `incompatible`. |
| `note` | multi_line_text_field | Human-readable explanation. |

The embedded app's Rules page CRUDs these; the theme's
`compatibility-matrix.liquid` reads them; Functions consult them when
deciding whether to block checkout.

## Where each field is consumed

| Field | Theme | Finder | Validation Function | Discount Function | Transform Function | Webhook |
| --- | --- | --- | --- | --- | --- | --- |
| `compatible_consoles` | matrix, badge | filter | match check | console intersection | — | — |
| `requires_accessory` | warning | warning | **blocks** | — | — | flag |
| `incompatible_with` | matrix | warning | — | — | — | — |
| `bundle_components` | — | — | — | — | **expand** | — |
| `bundle_type` | — | — | — | — | gate | — |
| `accessory_kind` | matrix | category filter | mixed-output check | kind requirement | — | — |
| `output_connector` | — | — | mixed-output check | — | — | — |
| `warning` | banner, badge | inline | — | — | — | — |
| `audit_status` | — | — | — | — | — | **writes** |

Every column reads from `custom.*` or from the `console` /
`compatibility_rule` metaobjects. There is no separate database, no
out-of-band syncing, and no place to "forget" to update.
