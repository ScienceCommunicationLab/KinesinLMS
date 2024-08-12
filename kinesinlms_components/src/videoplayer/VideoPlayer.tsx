import React, { useRef, useState, VFC } from 'react';
import axios from 'axios';
import YouTube from 'react-youtube';

interface Props {
    video_id: string;
    course_run: string;
    course_slug: string;
    unit_node_slug: string;
    course_unit_id: number;
    course_unit_slug: string;
    block_uuid: string;
    block_id: number;
}

const VideoPlayer: VFC<Props> = ({
    video_id: videoID,
    course_run: courseRun,
    course_slug: courseSlug,
    unit_node_slug: unitNodeSlug,
    course_unit_id: courseUnitID,
    course_unit_slug: courseUnitSlug,
    block_uuid: blockUUID,
    block_id: blockID,
}) => {
    const [showReplayButton, setShowReplayButton] = useState(false);
    const [autoPlay, setAutoPlay] = useState(0);

    const videoRef = useRef<YouTube>(null);

    const trackEvent = (videoEventType: string) => {
        axios({
            method: 'post',
            url: '/api/tracking/',
            withCredentials: true,
            xsrfCookieName: 'csrftoken',
            xsrfHeaderName: 'X-CSRFToken',
            data: {
                "event_type": "kinesinlms.course.video.activity",
                "course_run": courseRun,
                "course_slug": courseSlug,
                "unit_node_slug": unitNodeSlug,
                "course_unit_id": courseUnitID,
                "course_unit_slug": courseUnitSlug,
                "block_id": blockID,
                "block_uuid": blockUUID,
                "event_data": {
                    "video_id": videoID,
                    "video_event_type": videoEventType
                }
            }
        }).catch((error) => {
            console.log("Error from server. Couldn't log video interaction event.");
            console.log(error);
        });
    };

    if (!videoID || videoID === '') {
        return (
            <div className="no-video-message-wrapper">
                <div className="no-video-message">(Video to be added...)</div>
            </div>
        );
    }

    if (showReplayButton) {
        return (
            <div className="replay-video-wrapper">
                <button
                    onClick={() => {
                        setShowReplayButton(false);
                        setAutoPlay(1);
                        trackEvent("kinesinlms.course.video.replay_clicked");
                        videoRef.current?.internalPlayer.playVideo();
                    }}
                    className="btn btn-primary replay-video-btn"
                >
                    Replay Video
                </button>
            </div>
        );
    }

    return (
        <YouTube
            ref={videoRef}
            videoId={videoID}
            id={`player_${videoID}`}
            opts={{
                // https://developers.google.com/youtube/player_parameters
                playerVars: {
                    autoplay: autoPlay,
                    enablejsapi: 1,
                    rel: 0,
                    origin: window.location.origin,
                }
            }}
            onPlay={() => trackEvent("kinesinlms.course.video.play")}
            onPause={() => trackEvent("kinesinlms.course.video.pause")}
            onEnd={() => {
                trackEvent("kinesinlms.course.video.end");
                setShowReplayButton(true);
            }}
            onError={() => trackEvent("kinesinlms.course.video.error")}
            onPlaybackRateChange={() => trackEvent("kinesinlms.course.video.playback_rate_change")}
            onPlaybackQualityChange={() => trackEvent("kinesinlms.course.video.playback_quality_change")}
        />
    )
};

export default VideoPlayer;
