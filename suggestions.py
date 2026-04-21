"""
Smart Suggestion Engine
Generates personalized suggestions based on usage data and risk level
"""


def get_risk_level(prediction, probabilities=None):
    """Determine risk level from model prediction"""
    risk_info = {
        'level': 'Unknown',
        'score': 0,
        'color': '#gray'
    }

    if probabilities is not None and len(probabilities) > 0:
        max_prob = max(probabilities) * 100

        if isinstance(prediction, str):
            pred_lower = prediction.lower()
            if any(word in pred_lower for word in ['high', 'severe', 'addicted', 'yes', '2', 'danger']):
                risk_info = {'level': 'High Risk', 'score': max_prob, 'color': '#e74c3c'}
            elif any(word in pred_lower for word in ['medium', 'moderate', 'mild', '1', 'warning']):
                risk_info = {'level': 'Medium Risk', 'score': max_prob, 'color': '#f39c12'}
            else:
                risk_info = {'level': 'Low Risk', 'score': max_prob, 'color': '#27ae60'}
        else:
            pred_val = float(prediction)
            if pred_val >= 2 or max_prob >= 70:
                risk_info = {'level': 'High Risk', 'score': max_prob, 'color': '#e74c3c'}
            elif pred_val >= 1 or max_prob >= 40:
                risk_info = {'level': 'Medium Risk', 'score': max_prob, 'color': '#f39c12'}
            else:
                risk_info = {'level': 'Low Risk', 'score': max_prob, 'color': '#27ae60'}
    else:
        if isinstance(prediction, str):
            pred_lower = prediction.lower()
            if any(word in pred_lower for word in ['high', 'severe', 'addicted', 'yes', '2', 'danger']):
                risk_info = {'level': 'High Risk', 'score': 85, 'color': '#e74c3c'}
            elif any(word in pred_lower for word in ['medium', 'moderate', 'mild', '1', 'warning']):
                risk_info = {'level': 'Medium Risk', 'score': 55, 'color': '#f39c12'}
            else:
                risk_info = {'level': 'Low Risk', 'score': 25, 'color': '#27ae60'}
        else:
            pred_val = float(prediction)
            if pred_val >= 2:
                risk_info = {'level': 'High Risk', 'score': 85, 'color': '#e74c3c'}
            elif pred_val >= 1:
                risk_info = {'level': 'Medium Risk', 'score': 55, 'color': '#f39c12'}
            else:
                risk_info = {'level': 'Low Risk', 'score': 25, 'color': '#27ae60'}

    return risk_info


def generate_suggestions(risk_level, user_data=None):
    """Generate personalized suggestions based on risk level and usage data"""

    suggestions = {
        'immediate_actions': [],
        'daily_habits': [],
        'long_term_goals': [],
        'apps_recommended': [],
        'health_tips': []
    }

    if 'high' in risk_level.lower():
        suggestions['immediate_actions'] = [
            "🚨 Set a strict daily screen time limit of 3 hours",
            "📱 Enable Do Not Disturb mode during work/study hours",
            "🔕 Turn off ALL non-essential notifications immediately",
            "🛏️ Stop using phone 1 hour before bedtime",
            "📵 Create phone-free zones (bedroom, dining table)"
        ]
        suggestions['daily_habits'] = [
            "⏰ Check phone only at scheduled times (every 2 hours)",
            "📚 Replace 30 min of social media with reading daily",
            "🚶 Take a 15-minute walk without your phone",
            "🧘 Practice 10 minutes of mindfulness meditation",
            "📝 Keep a usage journal - write how you feel after each session",
            "👥 Have at least 1 face-to-face conversation daily"
        ]
        suggestions['long_term_goals'] = [
            "🎯 Reduce screen time by 1 hour each week",
            "🏃 Join a physical activity or sport",
            "📖 Develop a phone-free hobby (painting, cooking, music)",
            "🧠 Consider speaking with a counselor about digital wellness",
            "📅 Plan a full digital detox day once a month"
        ]
        suggestions['apps_recommended'] = [
            "Forest - Stay focused, plant virtual trees",
            "Digital Wellbeing - Built-in Android tracker",
            "Screen Time - Built-in iOS tracker",
            "Freedom - Block distracting apps & websites",
            "Headspace - Meditation and mindfulness"
        ]
        suggestions['health_tips'] = [
            "⚠️ Excessive phone use is linked to anxiety and depression",
            "👁️ Follow the 20-20-20 rule (every 20 min, look 20 feet away for 20 sec)",
            "💤 Blue light disrupts sleep - use night mode after 8 PM",
            "🦴 Phone neck can cause cervical spine issues",
            "🧠 Constant notifications increase cortisol (stress hormone)"
        ]

    elif 'medium' in risk_level.lower():
        suggestions['immediate_actions'] = [
            "⚡ Set a daily screen time limit of 4-5 hours",
            "🔔 Reduce notification permissions for social media apps",
            "📵 Keep phone away during meals and conversations",
            "🌙 Enable night mode / blue light filter after 8 PM"
        ]
        suggestions['daily_habits'] = [
            "📊 Monitor your daily usage with built-in screen time tools",
            "🏋️ Replace 20 min of scrolling with exercise",
            "📖 Read a physical book for 15 minutes daily",
            "🎵 Listen to music or podcast instead of scrolling",
            "⏱️ Use Pomodoro technique: 25 min work, 5 min phone"
        ]
        suggestions['long_term_goals'] = [
            "🎯 Aim to bring screen time under 3 hours/day in 1 month",
            "🌿 Develop 2 offline hobbies this month",
            "📅 Have one phone-free evening per week",
            "🤝 Strengthen in-person relationships"
        ]
        suggestions['apps_recommended'] = [
            "Forest - Gamified focus timer",
            "Moment - Track and limit usage",
            "Flipd - Lock your phone during focus time",
            "Calm - Sleep and relaxation"
        ]
        suggestions['health_tips'] = [
            "👀 Take regular eye breaks while using phone",
            "🧘 Practice deep breathing when you feel urge to check phone",
            "🚶 Walk for 10 minutes after every hour of screen time",
            "💧 Stay hydrated - set phone reminders for water intake"
        ]

    else:
        suggestions['immediate_actions'] = [
            "✅ Great job! You have healthy phone usage habits",
            "📱 Continue monitoring your usage weekly",
            "🛡️ Keep notifications limited to essentials only"
        ]
        suggestions['daily_habits'] = [
            "🌟 Maintain your current balanced routine",
            "📊 Review your screen time report weekly",
            "🏃 Keep up physical activities and outdoor time",
            "📚 Continue prioritizing productive app usage",
            "👨‍👩‍👧 Keep spending quality offline time with family"
        ]
        suggestions['long_term_goals'] = [
            "🎯 Help others develop healthy phone habits",
            "📖 Explore digital wellness and share knowledge",
            "🧠 Use your free time for skill development",
            "💪 You're a role model for balanced tech use!"
        ]
        suggestions['apps_recommended'] = [
            "Todoist - Productivity and task management",
            "Duolingo - Learn a new language",
            "Kindle - Read books on your phone productively",
            "Coursera - Online learning"
        ]
        suggestions['health_tips'] = [
            "👍 Your phone habits support good mental health",
            "🌿 Keep practicing digital wellness",
            "😊 Balanced usage reduces stress and improves sleep",
            "🧠 Your brain thanks you for the healthy boundaries!"
        ]

    if user_data:
        personal = analyze_user_data(user_data)
        suggestions['personalized'] = personal

    return suggestions


def analyze_user_data(data):
    """Generate personalized tips based on specific user input values"""
    tips = []

    try:
        for key, value in data.items():
            key_lower = key.lower()
            try:
                val = float(value)
            except (ValueError, TypeError):
                continue

            if 'screen' in key_lower and 'time' in key_lower:
                if val > 8:
                    tips.append(f"📱 Your screen time of {val}h is very high. Try reducing by 2h starting today.")
                elif val > 5:
                    tips.append(f"📱 Your screen time of {val}h is above average. Aim for under 4 hours.")

            if 'social' in key_lower:
                if val > 3:
                    tips.append(f"📲 You spend {val}h on social media. Try a 1-day social media detox this week.")

            if 'night' in key_lower or 'sleep' in key_lower:
                if val > 5:
                    tips.append(f"🌙 Checking phone {int(val)} times at night is harming your sleep quality.")

            if 'notification' in key_lower:
                if val > 100:
                    tips.append(f"🔔 {int(val)} notifications/day is overwhelming. Disable non-essential ones.")

            if 'gaming' in key_lower or 'game' in key_lower:
                if val > 2:
                    tips.append(f"🎮 {val}h of gaming daily. Set a timer to avoid marathon sessions.")

            if 'app' in key_lower and 'open' in key_lower:
                if val > 60:
                    tips.append(f"📂 Opening apps {int(val)} times/day shows compulsive behavior. Try batching.")

            if 'age' in key_lower:
                if val < 18:
                    tips.append("👶 Young users are more vulnerable. Parental guidance recommended.")
                elif val > 50:
                    tips.append("👴 Extended screen use may cause eye strain. Take frequent breaks.")

    except Exception:
        pass

    if not tips:
        tips.append("📊 Track your usage for a week to get more personalized insights!")

    return tips