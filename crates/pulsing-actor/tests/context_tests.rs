use pulsing_actor::actor::ActorId;
use pulsing_actor::prelude::*;
use std::sync::atomic::{AtomicI32, Ordering};
use std::sync::Arc;
use std::time::Duration;

#[derive(Serialize, Deserialize, Debug, PartialEq)]
struct Ping {
    value: i32,
}

#[derive(Serialize, Deserialize, Debug, PartialEq)]
struct Pong {
    value: i32,
}

#[derive(Serialize, Deserialize, Debug)]
struct ScheduledMsg {
    increment: i32,
}

#[derive(Serialize, Deserialize, Debug)]
struct GetValue;

struct Target;

#[async_trait]
impl Actor for Target {
    async fn receive(
        &mut self,
        msg: Message,
        _ctx: &mut ActorContext,
    ) -> anyhow::Result<Message> {
        let ping: Ping = msg.unpack()?;
        Message::pack(&Pong {
            value: ping.value + 1,
        })
    }
}

struct Forwarder {
    target: ActorId,
}

#[async_trait]
impl Actor for Forwarder {
    async fn receive(
        &mut self,
        msg: Message,
        ctx: &mut ActorContext,
    ) -> anyhow::Result<Message> {
        let ping: Ping = msg.unpack()?;
        let target_ref = ctx.actor_ref(&self.target).await?;
        let pong: Pong = target_ref.ask(Ping { value: ping.value }).await?;
        Message::pack(&pong)
    }
}

#[tokio::test]
async fn actor_context_can_resolve_actor_ref() {
    let system = ActorSystem::new(SystemConfig::standalone()).await.unwrap();

    let target_ref = system.spawn("target", Target).await.unwrap();
    let forwarder_ref = system
        .spawn(
            "forwarder",
            Forwarder {
                target: *target_ref.id(),
            },
        )
        .await
        .unwrap();

    let resp: Pong = forwarder_ref.ask(Ping { value: 41 }).await.unwrap();
    assert_eq!(resp.value, 42);
}
