package com.kendall.finapk.api

import com.kendall.finapk.BuildConfig
import com.kendall.finapk.model.TransactionEvent
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class BackendClient(
    private val baseUrl: String = BuildConfig.BASE_URL
) {
    fun login(username: String, password: String): LoginResult {
        val payload = JSONObject()
            .put("username", username)
            .put("password", password)

        val conn = openPost("$baseUrl/api/mobile/login")
        writeJson(conn, payload)

        return if (conn.responseCode in 200..299) {
            val response = conn.inputStream.bufferedReader().use { it.readText() }
            val obj = JSONObject(response)
            LoginResult(
                token = obj.optString("token"),
                userId = obj.optString("user_id"),
                username = obj.optString("username", username)
            )
        } else {
            throw IllegalStateException("Login falló (${conn.responseCode}).")
        }
    }

    fun uploadTransaction(token: String, event: TransactionEvent) {
        val payload = JSONObject()
            .put("source", event.source)
            .put("amount", event.amount)
            .put("merchant", event.merchant)
            .put("tx_date", event.txDate)
            .put("tx_time", event.txTime)
            .put("raw_text", event.rawText)

        val conn = openPost("$baseUrl/api/mobile/ingest")
        conn.setRequestProperty("Authorization", "Bearer $token")
        writeJson(conn, payload)

        if (conn.responseCode !in 200..299) {
            throw IllegalStateException("Ingest falló (${conn.responseCode}).")
        }
    }

    private fun openPost(url: String): HttpURLConnection {
        val conn = URL(url).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.connectTimeout = 10000
        conn.readTimeout = 10000
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        return conn
    }

    private fun writeJson(conn: HttpURLConnection, payload: JSONObject) {
        OutputStreamWriter(conn.outputStream).use { it.write(payload.toString()) }
    }
}

data class LoginResult(
    val token: String,
    val userId: String,
    val username: String
)
