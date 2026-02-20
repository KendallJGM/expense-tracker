package com.kendall.finapk.auth

import android.content.Context

class SessionManager(context: Context) {
    private val prefs = context.getSharedPreferences("fin_session", Context.MODE_PRIVATE)

    fun saveSession(token: String, userId: String, username: String) {
        prefs.edit()
            .putString(KEY_TOKEN, token)
            .putString(KEY_USER_ID, userId)
            .putString(KEY_USERNAME, username)
            .apply()
    }

    fun token(): String? = prefs.getString(KEY_TOKEN, null)
    fun userId(): String? = prefs.getString(KEY_USER_ID, null)
    fun username(): String? = prefs.getString(KEY_USERNAME, null)
    fun isLoggedIn(): Boolean = !token().isNullOrBlank()

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_TOKEN = "token"
        private const val KEY_USER_ID = "user_id"
        private const val KEY_USERNAME = "username"
    }
}
