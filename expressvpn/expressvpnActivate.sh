#!/usr/bin/expect
spawn expressvpn activate
expect {
    "code:" {
        send "$env(EXPRESS_VPN_ACTIVATION_CODE)\r"
        expect "information."
        send "n\r"
    }
    "Already activated" {send "n\r"}
}
expect eof
