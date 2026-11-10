#include <pcl/point_types.h>
#include <pcl/point_cloud.h>
#include <pcl/filters/voxel_grid.h>
#include <fstream>
int main(int argc,char**argv){
 if(argc!=3)return 2;
 std::ifstream in(argv[1],std::ios::binary);
 auto cloud=pcl::make_shared<pcl::PointCloud<pcl::PointXYZI>>();float v[4];
 while(in.read(reinterpret_cast<char*>(v),sizeof(v))){pcl::PointXYZI p;p.x=v[0];p.y=v[1];p.z=v[2];p.intensity=v[3];cloud->push_back(p);}
 pcl::VoxelGrid<pcl::PointXYZI> filter;filter.setLeafSize(.2f,.2f,.2f);filter.setInputCloud(cloud);pcl::PointCloud<pcl::PointXYZI> out;filter.filter(out);
 std::ofstream file(argv[2],std::ios::binary);
 for(const auto&p:out){float a[4]={p.x,p.y,p.z,p.intensity};file.write(reinterpret_cast<char*>(a),sizeof(a));}
 return file.good()?0:3;
}
