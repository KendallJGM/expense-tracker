package com.kendall.finapk.ingestion

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import com.kendall.finapk.api.BackendClient
import com.kendall.finapk.auth.SessionManager
import kotlin.concurrent.thread

class FinNotificationListenerService : NotificationListenerService() {
    private lateinit var session: SessionManager
    private lateinit var dedupStore: DedupStore
    private val backend = BackendClient()

    override fun onCreate() {
        super.onCreate()
        session = SessionManager(this)
        dedupStore = DedupStore(this)
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (!session.isLoggedIn()) return

        val extras = sbn.notification.extras
        val title = extras.getString("android.title") ?: ""
        val text = extras.getCharSequence("android.text")?.toString() ?: ""
        val whole = "$title $text".trim()
        if (whole.isBlank()) return

        val pkg = sbn.packageName
        val event = when {
            pkg.contains("wallet", ignoreCase = true) || pkg == "com.google.android.apps.walletnfcrel" -> {
                NotificationParser.parseWallet(whole)
            }
            pkg.contains("gmail", ignoreCase = true) || pkg.contains("google.android.gm", ignoreCase = true) -> {
                NotificationParser.parseBcrEmailNotification(whole)
            }
            else -> null
        } ?: return

        val userId = session.userId() ?: return
        val token = session.token() ?: return

        if (!dedupStore.shouldSend(userId, event.txDate, event.amount, event.merchant)) return

        thread {
            runCatching {
                backend.uploadTransaction(token, event)
            }
        }
    }
}
