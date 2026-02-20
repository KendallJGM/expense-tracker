package com.kendall.finapk

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.kendall.finapk.BuildConfig
import com.kendall.finapk.auth.SessionManager

class MainActivity : AppCompatActivity() {
    private lateinit var session: SessionManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        session = SessionManager(this)

        if (!session.isLoggedIn()) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        setContentView(R.layout.activity_main)

        val status = findViewById<TextView>(R.id.statusText)
        val openNotifSettings = findViewById<Button>(R.id.notificationAccessButton)
        val logout = findViewById<Button>(R.id.logoutButton)

        status.text = "Usuario activo: ${session.username()}\nServidor: ${BuildConfig.BASE_URL}"

        openNotifSettings.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        logout.setOnClickListener {
            session.clear()
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }
    }
}
