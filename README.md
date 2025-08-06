# erc-youth

**After pulling the updates**
Run these sql queries to update the existing database to match the updates without reseting the db:
```postgresql
-- 1. User-related CASCADE constraints
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_sender_id_fkey;
ALTER TABLE messages ADD CONSTRAINT messages_sender_id_fkey 
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE chat_room_members DROP CONSTRAINT IF EXISTS chat_room_members_user_id_fkey;
ALTER TABLE chat_room_members ADD CONSTRAINT chat_room_members_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE message_reactions DROP CONSTRAINT IF EXISTS message_reactions_user_id_fkey;
ALTER TABLE message_reactions ADD CONSTRAINT message_reactions_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE message_read_receipts DROP CONSTRAINT IF EXISTS message_read_receipts_user_id_fkey;
ALTER TABLE message_read_receipts ADD CONSTRAINT message_read_receipts_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_presence DROP CONSTRAINT IF EXISTS user_presence_user_id_fkey;
ALTER TABLE user_presence ADD CONSTRAINT user_presence_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE pinned_messages DROP CONSTRAINT IF EXISTS pinned_messages_pinned_by_user_id_fkey;
ALTER TABLE pinned_messages ADD CONSTRAINT pinned_messages_pinned_by_user_id_fkey 
    FOREIGN KEY (pinned_by_user_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_blocks DROP CONSTRAINT IF EXISTS user_blocks_blocker_id_fkey;
ALTER TABLE user_blocks ADD CONSTRAINT user_blocks_blocker_id_fkey 
    FOREIGN KEY (blocker_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_blocks DROP CONSTRAINT IF EXISTS user_blocks_blocked_id_fkey;
ALTER TABLE user_blocks ADD CONSTRAINT user_blocks_blocked_id_fkey 
    FOREIGN KEY (blocked_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_reports DROP CONSTRAINT IF EXISTS user_reports_reporter_id_fkey;
ALTER TABLE user_reports ADD CONSTRAINT user_reports_reporter_id_fkey 
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE;

ALTER TABLE user_reports DROP CONSTRAINT IF EXISTS user_reports_reported_id_fkey;
ALTER TABLE user_reports ADD CONSTRAINT user_reports_reported_id_fkey 
    FOREIGN KEY (reported_id) REFERENCES users(id) ON DELETE CASCADE;

-- 2. Message-related CASCADE constraints (THIS WAS MISSING!)
ALTER TABLE message_read_receipts DROP CONSTRAINT IF EXISTS message_read_receipts_message_id_fkey;
ALTER TABLE message_read_receipts ADD CONSTRAINT message_read_receipts_message_id_fkey 
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE;

ALTER TABLE message_reactions DROP CONSTRAINT IF EXISTS message_reactions_message_id_fkey;
ALTER TABLE message_reactions ADD CONSTRAINT message_reactions_message_id_fkey 
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE;

ALTER TABLE message_edit_history DROP CONSTRAINT IF EXISTS message_edit_history_message_id_fkey;
ALTER TABLE message_edit_history ADD CONSTRAINT message_edit_history_message_id_fkey 
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE;

ALTER TABLE pinned_messages DROP CONSTRAINT IF EXISTS pinned_messages_message_id_fkey;
ALTER TABLE pinned_messages ADD CONSTRAINT pinned_messages_message_id_fkey 
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE;

-- 3. Chat room CASCADE constraints
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_chat_room_id_fkey;
ALTER TABLE messages ADD CONSTRAINT messages_chat_room_id_fkey 
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE;

ALTER TABLE chat_room_members DROP CONSTRAINT IF EXISTS chat_room_members_chat_room_id_fkey;
ALTER TABLE chat_room_members ADD CONSTRAINT chat_room_members_chat_room_id_fkey 
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE;

ALTER TABLE pinned_messages DROP CONSTRAINT IF EXISTS pinned_messages_chat_room_id_fkey;
ALTER TABLE pinned_messages ADD CONSTRAINT pinned_messages_chat_room_id_fkey 
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE;

ALTER TABLE chat_analytics DROP CONSTRAINT IF EXISTS chat_analytics_chat_room_id_fkey;
ALTER TABLE chat_analytics ADD CONSTRAINT chat_analytics_chat_room_id_fkey 
    FOREIGN KEY (chat_room_id) REFERENCES chat_rooms(id) ON DELETE CASCADE;

-- 4. For self-referencing and optional references, use SET NULL
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_reply_to_message_id_fkey;
ALTER TABLE messages ADD CONSTRAINT messages_reply_to_message_id_fkey 
    FOREIGN KEY (reply_to_message_id) REFERENCES messages(id) ON DELETE SET NULL;

ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_forwarded_from_message_id_fkey;
ALTER TABLE messages ADD CONSTRAINT messages_forwarded_from_message_id_fkey 
    FOREIGN KEY (forwarded_from_message_id) REFERENCES messages(id) ON DELETE SET NULL;

ALTER TABLE user_reports DROP CONSTRAINT IF EXISTS user_reports_message_id_fkey;
ALTER TABLE user_reports ADD CONSTRAINT user_reports_message_id_fkey 
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE SET NULL;

ALTER TABLE chat_room_members DROP CONSTRAINT IF EXISTS chat_room_members_last_read_message_id_fkey;
ALTER TABLE chat_room_members ADD CONSTRAINT chat_room_members_last_read_message_id_fkey 
    FOREIGN KEY (last_read_message_id) REFERENCES messages(id) ON DELETE SET NULL;

ALTER TABLE user_presence DROP CONSTRAINT IF EXISTS user_presence_is_typing_in_room_fkey;
ALTER TABLE user_presence ADD CONSTRAINT user_presence_is_typing_in_room_fkey 
    FOREIGN KEY (is_typing_in_room) REFERENCES chat_rooms(id) ON DELETE SET NULL;
```