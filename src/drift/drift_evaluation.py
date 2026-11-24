"""One-alert-per-event matching with separate repeated and stationary alerts."""


def evaluate(alerts,events,length,warmup=256,tolerance=512):
    matched=set();delays=[];false=repeat=0
    eligible=[i for i in alerts if i>=warmup]
    for index in eligible:
        candidates=[event for event in events if event<=index<event+tolerance]
        pending=[event for event in candidates if event not in matched]
        if pending:
            event=min(pending);matched.add(event);delays.append(index-event)
        elif candidates:repeat+=1
        else:false+=1
    return {'true_episodes':len(events),'detected_episodes':len(matched),'misses':len(events)-len(matched),
            'recall':len(matched)/len(events) if events else None,'mean_delay_observations':sum(delays)/len(delays) if delays else None,
            'false_alarms':false,'repeated_episode_alerts':repeat,'false_per_1000':1000*false/(length-warmup),
            'alert_precision':len(matched)/len(eligible) if eligible else None,'alerts':len(eligible)}
