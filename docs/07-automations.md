# 7. Automations

Entity ids follow `device_name`; with `IC-7300` they are e.g. `sensor.ic_7300_frequency` and `event.ic_7300_js8call`. Check yours under the device in Home Assistant.

## A JS8 message for me → phone notification

The event entity's state is the time of the last event, so a state trigger fires for every event, even two of the same type in a row. A condition picks the type:

```yaml
automation:
  - alias: JS8 message for me
    triggers:
      - trigger: state
        entity_id: event.ic_7300_js8call
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.event_type == 'message_to_me' }}"
    actions:
      - action: notify.mobile_app_my_phone
        data:
          title: "JS8 from {{ trigger.to_state.attributes.from }}"
          message: >
            {{ trigger.to_state.attributes.text }}
            (SNR {{ trigger.to_state.attributes.snr }} dB)
```

## Radio left on

```yaml
automation:
  - alias: Radio still on at midnight
    triggers:
      - trigger: time
        at: "00:00:00"
    conditions:
      - condition: state
        entity_id: binary_sensor.ic_7300_online
        state: "on"
    actions:
      - action: notify.mobile_app_my_phone
        data:
          message: "The IC-7300 is still on ({{ states('sensor.ic_7300_frequency') }} MHz)."
```

More in [examples/automations.yaml](../examples/automations.yaml).
