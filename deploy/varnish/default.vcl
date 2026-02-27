vcl 4.1;

backend default {
    .host = "127.0.0.1";
    .port = "8080"; # Nginx backend if Varnish sits in front of Nginx
}

sub vcl_recv {
    if (req.method != "GET" && req.method != "HEAD") {
        return (pass);
    }
    if (req.url ~ "^/(login|login-2fa|logout|register|forgot-password|reset-password|settings|security-settings)") {
        return (pass);
    }
    if (req.http.Cookie) {
        return (pass);
    }
}

sub vcl_backend_response {
    if (bereq.url ~ "^/app/static/") {
        set beresp.ttl = 1h;
    } else {
        set beresp.ttl = 2m;
    }
}
