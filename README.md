# Surveillance Station Home Mode for HomeAssistant

This component allows you to set the home or away state for Synology Surveillance Station from within HomeAssistant.

To enable this platform in your installation, add the following to your configuration.yaml file:

``` yaml
light:
  - platform: synologysurveillance
  url: https://192.168.x.x:5001
  username: secret_username
  password: secret_password
  verify_ssl: false
```

* note that you must replace the url/username/password values above with the correct ones for your setup.

Once these steps are complete, restart your instance of HomeAssistant and you should then have a new switch available for automation.

![capture.png](capture.png)