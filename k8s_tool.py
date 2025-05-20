import json
import math
import shlex
from datetime import datetime
from functools import wraps
from json import JSONDecodeError

from kubernetes import client
from kubernetes.client import Configuration, CoreV1Api, ApiClient, AppsV1Api, ExtensionsV1beta1Api, CustomObjectsApi, \
    NetworkingV1Api
from kubernetes.client.rest import ApiException
import logging


def catch_api_exception(func):
    @wraps(func)
    def wrapper(self, *_args, **_kwargs):
        try:
            result = func(self, *_args, **_kwargs)
        except ApiException as e:
            self.logger.exception(e)
            try:
                error = json.loads(e.body)
            except JSONDecodeError:
                message = e.body
            else:
                message = error.get("message", str(e))
            return False, message
        else:
            return True, result

    return wrapper


class KubernetesClient:
    def __init__(self, host, token, logger=None, verify_ssl=False):
        self.__set_configuration(host, token, verify_ssl=verify_ssl)
        self.logger = logger or logging.getLogger(__name__)
        self._api_client = None
        self._core_client = None
        self._app_v1_api = None
        self._extensions_v1_beta1_api = None
        self._custom_object_api = None
        self._networking_v1_api = None

    def __set_configuration(self, host, token, verify_ssl=False):
        configuration = Configuration()
        configuration.verify_ssl = verify_ssl
        configuration.host = host
        configuration.api_key = {"authorization": "Bearer " + token}
        self.configuration = configuration

    @property
    def api_client(self):
        if not self._api_client:
            self._api_client = ApiClient(configuration=self.configuration)
        return self._api_client

    @property
    def core_v1_api(self):
        if not self._core_client:
            self._core_client = CoreV1Api(api_client=self.api_client)
        return self._core_client

    @property
    def app_v1_api(self):
        if not self._app_v1_api:
            self._app_v1_api = AppsV1Api(api_client=self.api_client)
        return self._app_v1_api

    @property
    def networking_v1_api(self):
        if not self._networking_v1_api:
            self._networking_v1_api = NetworkingV1Api(api_client=self.api_client)
        return self._networking_v1_api

    @property
    def extensions_v1_beta1_api(self):
        if not self._extensions_v1_beta1_api:
            self._extensions_v1_beta1_api = ExtensionsV1beta1Api(api_client=self.api_client)
        return self._extensions_v1_beta1_api

    def sanitize_for_serialization(self, obj):
        return self.api_client.sanitize_for_serialization(obj)

    @property
    def custom_object_api(self):
        if not self._custom_object_api:
            self._custom_object_api = CustomObjectsApi(api_client=self.api_client)
        return self._custom_object_api

    @catch_api_exception
    def list_namespace(self):
        results = self.core_v1_api.list_namespace()
        namespaces = []
        for item in results.items:
            namespaces.append(item.metadata.name)
        return namespaces

    @catch_api_exception
    def create_namespace(self, namespace):
        ns = client.V1Namespace()
        ns.metadata = client.V1ObjectMeta(name=namespace)
        return self.core_v1_api.create_namespace(body=ns)

    @catch_api_exception
    def list_namespaced_deployment(self, namespace, **kwargs):
        return self.app_v1_api.list_namespaced_deployment(namespace, **kwargs)

    @catch_api_exception
    def read_namespaced_deployment(self, name, namespace, **kwargs) -> (bool, client.V1Deployment):
        return self.app_v1_api.read_namespaced_deployment(name, namespace, **kwargs)

    def is_deployment_exists(self, name, namespace, **kwargs):
        try:
            result = self.app_v1_api.read_namespaced_deployment(name, namespace, **kwargs)
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        else:
            return result

    @catch_api_exception
    def read_namespaced_deployment_status(self, name, namespace, **kwargs) -> (bool, client.V1DeploymentStatus):
        return self.app_v1_api.read_namespaced_deployment_status(name, namespace, **kwargs)

    @catch_api_exception
    def patch_namespaced_deployment(self, name, namespace, body, **kwargs):
        return self.app_v1_api.patch_namespaced_deployment(name, namespace, body, **kwargs)

    @catch_api_exception
    def create_namespaced_deployment(self, namespace, body, **kwargs):
        return self.app_v1_api.create_namespaced_deployment(namespace, body, **kwargs)

    @catch_api_exception
    def replace_namespaced_deployment(self, name, namespace, body, **kwargs):
        return self.app_v1_api.replace_namespaced_deployment(name, namespace, body, **kwargs)

    @catch_api_exception
    def list_namespaces_deployment(self, namespaces, **kwargs):
        results = []
        for namespace in namespaces:
            result = self.app_v1_api.list_namespaced_deployment(namespace, **kwargs)
            results.extend(result.items)
        return results

    @catch_api_exception
    def delete_namespaced_deployment(self, name, namespace, **kwargs):
        return self.app_v1_api.delete_namespaced_deployment(name, namespace, **kwargs)

    @catch_api_exception
    def list_namespaced_pod(self, namespace, **kwargs):
        return self.core_v1_api.list_namespaced_pod(namespace, **kwargs)

    @catch_api_exception
    def list_namespaced_persistent_volume_claim(self, namespace, **kwargs):
        return self.core_v1_api.list_namespaced_persistent_volume_claim(namespace, **kwargs)

    @catch_api_exception
    def list_namespaced_config_map(self, namespace, **kwargs):
        return self.core_v1_api.list_namespaced_config_map(namespace, **kwargs)

    @catch_api_exception
    def create_namespaced_config_map(self, namespace, body, **kwargs):
        return self.core_v1_api.create_namespaced_config_map(namespace, body, **kwargs)

    @catch_api_exception
    def delete_namespaced_config_map(self, name, namespace, **kwargs):
        return self.core_v1_api.delete_namespaced_config_map(name, namespace, **kwargs)

    @catch_api_exception
    def read_namespaced_config_map(self, name, namespace, **kwargs):
        return self.core_v1_api.read_namespaced_config_map(name, namespace, **kwargs)

    @catch_api_exception
    def patch_namespaced_config_map(self, name, namespace, body, **kwargs):
        return self.core_v1_api.patch_namespaced_config_map(name, namespace, body, **kwargs)

    def is_config_map_exists(self, name, namespace):
        try:
            result = self.core_v1_api.read_namespaced_config_map(name, namespace)
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        else:
            return result

    @catch_api_exception
    def read_namespaced_secret(self, name, namespace, **kwargs):
        return self.core_v1_api.read_namespaced_secret(name, namespace, **kwargs)

    @catch_api_exception
    def create_namespaced_secret(self, namespace, body, **kwargs):
        return self.core_v1_api.create_namespaced_secret(namespace, body, **kwargs)

    @catch_api_exception
    def delete_namespaced_secret(self, name, namespace, **kwargs):
        return self.core_v1_api.delete_namespaced_secret(name, namespace, **kwargs)

    @catch_api_exception
    def patch_namespaced_secret(self, name, namespace, body, **kwargs):
        return self.core_v1_api.patch_namespaced_secret(name, namespace, body, **kwargs)

    @catch_api_exception
    def list_namespaced_secret(self, namespace, **kwargs):
        return self.core_v1_api.list_namespaced_secret(namespace, **kwargs)

    def is_secret_exists(self, name, namespace):
        try:
            result = self.core_v1_api.read_namespaced_secret(name, namespace)
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        else:
            return result

    @catch_api_exception
    def list_namespaced_event(self, namespace, **kwargs):
        return self.core_v1_api.list_namespaced_event(namespace, **kwargs)

    @catch_api_exception
    def list_namespaced_service(self, namespace, **kwargs):
        return self.core_v1_api.list_namespaced_service(namespace, **kwargs)

    @catch_api_exception
    def create_namespaced_service(self, namespace, body, **kwargs):
        return self.core_v1_api.create_namespaced_service(namespace, body, **kwargs)

    @catch_api_exception
    def patch_namespaced_service(self, name, namespace, body, **kwargs):
        return self.core_v1_api.patch_namespaced_service(name, namespace, body, **kwargs)

    @catch_api_exception
    def delete_namespaced_service(self, name, namespace, **kwargs):
        return self.core_v1_api.delete_namespaced_service(name, namespace, **kwargs)

    @catch_api_exception
    def list_namespaced_ingress(self, namespace, **kwargs):
        return self.networking_v1_api.list_namespaced_ingress(namespace, **kwargs)

    @catch_api_exception
    def create_namespaced_ingress(self, namespace, body, **kwargs):
        return self.networking_v1_api.create_namespaced_ingress(namespace, body, **kwargs)

    @catch_api_exception
    def patch_namespaced_ingress(self, name, namespace, body, **kwargs):
        return self.networking_v1_api.patch_namespaced_ingress(name, namespace, body, **kwargs)

    @catch_api_exception
    def delete_namespaced_ingress(self, name, namespace, **kwargs):
        return self.networking_v1_api.delete_namespaced_ingress(name, namespace, **kwargs)

    @catch_api_exception
    def read_namespaced_ingress(self, name, namespace, **kwargs) -> (bool, client.ExtensionsV1beta1Ingress):
        return self.networking_v1_api.read_namespaced_ingress(name, namespace, **kwargs)

    def is_service_exists(self, name, namespace):
        try:
            result = self.core_v1_api.read_namespaced_service(name, namespace)
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        else:
            return result

    def is_ingress_exists(self, name, namespace):
        try:
            result = self.networking_v1_api.read_namespaced_ingress(name, namespace)
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        else:
            return result

    @catch_api_exception
    def list_namespaced_replica_set(self, namespace, **kwargs):
        return self.app_v1_api.list_namespaced_replica_set(namespace, **kwargs)

    @catch_api_exception
    def read_namespaced_pod_log(self, name, namespace, **kwargs):
        return self.core_v1_api.read_namespaced_pod_log(name, namespace, **kwargs)

    @catch_api_exception
    def list_namespaced_virtual_service(self, namespace, **kwargs):
        result = self.custom_object_api.list_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "virtualservices", **kwargs)
        for key, value in result.items():
            if key == "items":
                return value
        return []

    @catch_api_exception
    def list_namespaced_gateway(self, namespace, **kwargs):
        result = self.custom_object_api.list_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "gateways", **kwargs)
        for key, value in result.items():
            if key == "items":
                return value
        return []

    @catch_api_exception
    def list_namespaced_destination_rule(self, namespace, **kwargs):
        result = self.custom_object_api.list_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "destinationrules", **kwargs)
        for key, value in result.items():
            if key == "items":
                return value
        return []

    @catch_api_exception
    def patch_namespaced_destination_rule(self, name, namespace, patch_body, **kwargs):
        return self.custom_object_api.patch_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "destinationrules", name, patch_body, **kwargs
        )

    @catch_api_exception
    def replace_namespaced_destination_rule(self, name, namespace, body, **kwargs):
        return self.custom_object_api.replace_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "destinationrules", name, body, **kwargs
        )

    @catch_api_exception
    def read_namespaced_virtual_service(self, name, namespace, **kwargs):
        return self.custom_object_api.get_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "virtualservices", name, **kwargs)

    @catch_api_exception
    def replace_namespaced_virtual_service(self, name, namespace, body, **kwargs):
        return self.custom_object_api.replace_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "virtualservices", name, body, **kwargs
        )

    def is_virtual_service_exists(self, name, namespace):
        try:
            result = self.custom_object_api.get_namespaced_custom_object(
                "networking.istio.io", "v1alpha3", namespace, "virtualservices", name
            )
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        else:
            return result

    @catch_api_exception
    def patch_namespaced_virtual_service(self, name, namespace, patch_body, **kwargs):
        return self.custom_object_api.patch_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "virtualservices", name, patch_body, **kwargs
        )

    @catch_api_exception
    def create_namespaced_virtual_service(self, name, version, namespace, **kwargs):
        body = {
            "apiVersion": "networking.istio.io/v1alpha3",
            "kind": "VirtualService",
            "metadata": {"name": name},
            "spec": {
                "hosts": [name],
                "http": [{
                    "route": [{
                        "destination": {
                            "host": name,
                            "subset": version
                        }
                    }]
                }]
            }
        }
        return self.custom_object_api.create_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "virtualservices", body, **kwargs
        )

    @catch_api_exception
    def create_namespaced_destination_rule(self, name, version, namespace, **kwargs):
        body = {
            "apiVersion": "networking.istio.io/v1alpha3",
            "kind": "DestinationRule",
            "metadata": {"name": name},
            "spec": {
                "host": name,
                "subsets": [{
                    "name": version,
                    "labels": {
                        "version": version
                    }
                }]
            }
        }
        return self.custom_object_api.create_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "destinationrules", body, **kwargs
        )

    @catch_api_exception
    def read_namespaced_destination_rule(self, name, namespace, **kwargs):
        return self.custom_object_api.get_namespaced_custom_object(
            "networking.istio.io", "v1alpha3", namespace, "destinationrules", name, **kwargs
        )

    def is_destination_rule_exists(self, name, namespace):
        try:
            result = self.custom_object_api.get_namespaced_custom_object(
                "networking.istio.io", "v1alpha3", namespace, "destinationrules", name
            )
        except ApiException as e:
            if e.status == 404:
                return False
            else:
                raise e
        else:
            return result


class KubernetesObject:

    @classmethod
    def create_config_map_object(cls, name, namespace, data, **kwargs) -> client.V1ConfigMap:
        obj = client.V1ConfigMap(
            api_version="v1",
            kind="ConfigMap",
            metadata=client.V1ObjectMeta(name=name, namespace=namespace, labels=kwargs.get("labels")),
            data=data
        )
        return obj

    @classmethod
    def create_secret_object(cls, name, namespace, data, **kwargs) -> client.V1Secret:
        obj = client.V1Secret(
            api_version="v1",
            kind="Secret",
            type="Opaque",
            metadata=client.V1ObjectMeta(name=name, namespace=namespace, labels=kwargs.get("labels")),
            data=data
        )
        return obj

    @classmethod
    def convert_dict_to_v1_probe(cls, data: dict):
        if not data:
            return None
        http_get = None
        tcp_socket = None
        _exec = None
        if http_get_data := data.get("http_get"):
            http_get = client.V1HTTPGetAction(
                path=http_get_data["path"], port=http_get_data["port"], scheme=http_get_data["scheme"]
            )
        if tcp_socket_data := data.get("tcp_socket"):
            tcp_socket = client.V1TCPSocketAction(port=tcp_socket_data["port"])
        if exec_data := data.get("_exec"):
            command_string = exec_data.get("command", '')
            command_list = shlex.split(command_string)
            _exec = client.V1ExecAction(command=command_list)
        obj = client.V1Probe(
            failure_threshold=data["failure_threshold"],
            http_get=http_get,
            tcp_socket=tcp_socket,
            _exec=_exec,
            initial_delay_seconds=data["initial_delay_seconds"],
            period_seconds=data["period_seconds"],
            success_threshold=data["success_threshold"],
            timeout_seconds=data["timeout_seconds"]
        )
        return obj

    @classmethod
    def convert_v1_probe_to_dict(cls, v1_probe: client.V1Probe):
        return v1_probe.to_dict()

    @classmethod
    def convert_dict_to_volumes(cls, data: dict):
        volumes_mounts = []
        volumes = []
        if not data:
            return None, None
        volumes_name_set = set()
        datetime_now = datetime.now().timestamp() * 1000
        offset = 0
        for volume in data:
            name_default = volume.get("name") or 'volume-%d' % (datetime_now + offset)
            offset += 1
            volume_type = volume["volume_type"]
            # 云盘挂载
            if volume_type == 1:
                name = 'volume-' + volume["mounted_source"]
                v1_volume = client.V1Volume(
                    name=name,
                    persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                        claim_name=volume["mounted_source"])
                )
            # 本地挂载
            elif volume_type == 2:
                name = name_default
                v1_volume = client.V1Volume(
                    name=name,
                    host_path=client.V1HostPathVolumeSource(path=volume["mounted_source"])
                )
            # 保密字典
            elif volume_type == 3:
                name = name_default
                v1_volume = client.V1Volume(
                    name=name,
                    secret=client.V1SecretVolumeSource(
                        secret_name=volume["mounted_source"], default_mode=420
                    )
                )
            # 配置项，如config_map
            elif volume_type == 4:
                name = name_default
                v1_volume = client.V1Volume(
                    name=name,
                    config_map=client.V1ConfigMapVolumeSource(
                        name=volume["mounted_source"], default_mode=420
                    )
                )
            # 临时目录
            elif volume_type == 5:
                name = name_default
                v1_volume = client.V1Volume(
                    name=name,
                    empty_dir=client.V1EmptyDirVolumeSource()
                )
            else:
                raise ValueError(f"未知盘符类型，无法挂载：{volume}")
            sub_path = volume["sub_path"] if volume.get("sub_path") else None
            volumes_mounts.append(
                client.V1VolumeMount(
                    mount_path=volume["container_path"],
                    name=name,
                    sub_path=sub_path
                )
            )
            if name not in volumes_name_set:
                volumes.append(v1_volume)
                volumes_name_set.add(name)
        return volumes_mounts, volumes

    @classmethod
    def convert_volumes_to_dict(cls, volume_mounts: [client.V1VolumeMount], volumes: [client.V1Volume]):
        volume_mounts = volume_mounts or []
        volumes = volumes or []
        name_info_map = {}
        for v in volumes:
            temp_info = {"name": v.name}
            # 云盘挂载
            if v.persistent_volume_claim is not None:
                temp_info["volume_type"] = 1
                temp_info["mounted_source"] = v.persistent_volume_claim.claim_name
            # 主机目录
            elif v.host_path is not None:
                temp_info["volume_type"] = 2
                temp_info["mounted_source"] = v.host_path.path
            # 保密字典
            elif v.secret is not None:
                temp_info["volume_type"] = 3
                temp_info["mounted_source"] = v.secret.secret_name
            # 配置项
            elif v.config_map is not None:
                temp_info["volume_type"] = 4
                temp_info["mounted_source"] = v.config_map.name
            # 临时目录
            elif v.empty_dir is not None:
                temp_info["volume_type"] = 5
                temp_info["mounted_source"] = '临时目录'
            else:
                raise ValueError("解析数据卷类型失败，请联系管理员")
            name_info_map[v.name] = temp_info
        results = []
        for m in volume_mounts:
            result = {
                "volume_type": name_info_map[m.name]["volume_type"],
                "mounted_source": name_info_map[m.name]["mounted_source"],
                "container_path": m.mount_path,
                "sub_path": m.sub_path if m.sub_path else '',
                "name": m.name
            }
            results.append(result)
        return results

    @classmethod
    def convert_dict_to_resources(cls, data: dict):
        if not data:
            return None
        resources = client.V1ResourceRequirements(
            limits=data.get("limits"),
            requests=data.get("requests")
        )
        return resources

    @classmethod
    def convert_resource_to_dict(cls, v1_resources: client.V1ResourceRequirements):
        return v1_resources.to_dict()
